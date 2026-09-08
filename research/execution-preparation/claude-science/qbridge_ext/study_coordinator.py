"""Scheduling component + spend ledger for protocol v0.4. NOT the full runner.

Scope (stated honestly): this module (1) enumerates the normative schedule
(stage 1 = blocks 0..19, stage 2 = blocks 20..39; within a block RS -> CMA-ES
-> LLM, protocol §8.1) over ONE DurableJournal so the runner's identity-change
detection sees the common history across blocks, (2) refuses to start any
(block, arm) twice (no replay, §7.5) and (3) accounts money by reserve-then-
reconcile against a fixed authority. It is not the whole-study launcher,
crash-recovery driver, masked-export step or freeze tool; those remain
separate, unimplemented work. Nothing here calls a provider or the objective.

Ledger rules (review 2026-09-08):
* every attempt reserves the FULL per-attempt cap (L x R_in + 8192 x R_out)
  before dispatch;
* an attempt whose applicable billing categories (prompt, completion,
  cached, cache_write) are ALL known integers is reconciled to the priced
  actual amount WITHOUT clipping; if that amount exceeds the cap, or prompt >
  L, or completion > 8192, or a cache category is nonzero, the attempt is
  marked contract_overrun and the ledger HALTS further dispatch;
* an attempt with ANY applicable category unknown keeps max(full cap, priced
  known part) forever and is usage_known=False; missing fields are never 0;
* the ceiling and scope come from an AuthorityRecord; there is no default.
"""

from __future__ import annotations

import re
from decimal import Context, Decimal, localcontext
from pathlib import Path

from qbridge.journal import DurableJournal

STAGES = {1: tuple(range(0, 20)), 2: tuple(range(20, 40))}
# Protocol v0.4 §8.1: "arms are executed in the fixed order RS -> CMA-ES -> LLM".
# Runner labels for those arms are RS, CMA, AI respectively.
ARM_ORDER = ("RS", "CMA", "AI")
OUTPUT_CAP = 8192
APPLICABLE_CATEGORIES = (
    "prompt_tokens",
    "completion_tokens",
    "cached_tokens",
    "cache_write_tokens",
)
_PREC = Context(prec=100)


class MonetaryCeilingReached(RuntimeError):
    """Not enough remaining authority (or attempt cap) to reserve one full attempt."""


class LedgerHalted(RuntimeError):
    """A billing-contract overrun was observed; no further dispatch is permitted."""


class ReplayRefused(RuntimeError):
    """A (block, arm) already started; the protocol forbids resuming it."""


def validate_money(value, name) -> Decimal:
    """Same grammar as qbridge.budget._money: nonnegative finite decimal string."""
    message = (
        f"{name} must be a nonnegative decimal string of at most 64 characters, "
        "value <= 1e12 and decimal exponent from -12 through 12"
    )
    if type(value) is not str or len(value) > 64:
        raise ValueError(message)
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", value) is None:
        raise ValueError(message)
    amount = Decimal(value)
    if not amount.is_finite() or amount > Decimal("1e12"):
        raise ValueError(message)
    if not -12 <= amount.as_tuple().exponent <= 12:
        raise ValueError(message)
    return amount


def validate_count(value, name, minimum, maximum) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be a native integer from {minimum} through {maximum}")
    return value


class SpendLedger:
    """Reserve-then-reconcile attempt accounting against a fixed USD ceiling."""

    def __init__(
        self,
        journal: DurableJournal,
        *,
        ceiling_usd: str,
        input_token_ceiling: int,
        input_usd_per_million: str,
        output_usd_per_million: str,
        scope: str,
    ):
        self.journal = journal
        if not isinstance(scope, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", scope):
            raise ValueError("scope must be a short identifier")
        self.scope = scope
        self.ceiling = validate_money(ceiling_usd, "ceiling_usd")
        self.L = validate_count(input_token_ceiling, "input_token_ceiling", 1, 1_000_000_000)
        self.R_in = validate_money(input_usd_per_million, "input_usd_per_million")
        self.R_out = validate_money(output_usd_per_million, "output_usd_per_million")
        self._open = None

    def full_attempt_cap(self) -> Decimal:
        with localcontext(_PREC):
            return (Decimal(self.L) * self.R_in + Decimal(OUTPUT_CAP) * self.R_out) / 1_000_000

    def price_known(self, usage: dict) -> Decimal:
        """Priced amount of the KNOWN prompt/completion counts, never clipped."""
        with localcontext(_PREC):
            prompt = Decimal(usage.get("prompt_tokens") or 0)
            completion = Decimal(usage.get("completion_tokens") or 0)
            return (prompt * self.R_in + completion * self.R_out) / 1_000_000

    def assess(self, usage: dict | None) -> dict:
        """Classify an outcome: known/unknown billing, overrun flags, amount to book."""
        cap = self.full_attempt_cap()
        if not isinstance(usage, dict):
            return {"usage_known": False, "overrun": [], "usd": cap}
        known = all(type(usage.get(k)) is int and usage.get(k) >= 0 for k in APPLICABLE_CATEGORIES)
        overrun = []
        if type(usage.get("prompt_tokens")) is int and usage["prompt_tokens"] > self.L:
            overrun.append("prompt_tokens_exceed_input_ceiling")
        if type(usage.get("completion_tokens")) is int and usage["completion_tokens"] > OUTPUT_CAP:
            overrun.append("completion_tokens_exceed_output_cap")
        for key in ("cached_tokens", "cache_write_tokens"):
            if type(usage.get(key)) is int and usage[key] != 0:
                overrun.append(f"{key}_nonzero")
        priced = self.price_known(usage)
        if known:
            if priced > cap:
                overrun.append("priced_amount_exceeds_reservation")
            return {"usage_known": True, "overrun": overrun, "usd": priced}
        # incomplete applicable billing: retain the full reservation, never understate
        with localcontext(_PREC):
            amount = max(cap, priced)
        return {"usage_known": False, "overrun": overrun, "usd": amount}

    def totals(self) -> dict:
        with localcontext(_PREC):
            reserved = Decimal(0)
            reconciled = Decimal(0)
            unknown = 0
            attempts = 0
            halted = False
            for event in self.journal.read_events():
                if event.get("scope") != self.scope:
                    continue
                kind = event.get("kind")
                if kind == "spend_reserved":
                    attempts += 1
                    reserved += Decimal(event["usd"])
                elif kind == "spend_reconciled":
                    reserved -= Decimal(event["reserved_usd"])
                    reconciled += Decimal(event["usd"])
                    if event.get("usage_known") is False:
                        unknown += 1
                    if event.get("overrun"):
                        halted = True
            return {
                "attempts": attempts,
                "open_reservations_usd": str(reserved),
                "reconciled_usd": str(reconciled),
                "committed_usd": str(reserved + reconciled),
                "remaining_usd": str(self.ceiling - reserved - reconciled),
                "unknown_usage_attempts": unknown,
                "ceiling_usd": str(self.ceiling),
                "halted": halted,
            }

    def reserve_attempt(self, *, cap: int | None = None) -> str:
        if self._open is not None:
            raise RuntimeError("previous attempt not reconciled")
        totals = self.totals()
        if totals["halted"]:
            raise LedgerHalted("billing-contract overrun recorded; dispatch halted")
        if cap is not None and totals["attempts"] >= cap:
            raise MonetaryCeilingReached(f"attempt cap {cap} reached")
        need = self.full_attempt_cap()
        if Decimal(totals["remaining_usd"]) < need:
            raise MonetaryCeilingReached(
                f"remaining {totals['remaining_usd']} < full attempt cap {need}"
            )
        key = f"{self.scope}:{totals['attempts'] + 1}"
        self.journal.append("spend_reserved", scope=self.scope, key=key, usd=str(need))
        self._open = (key, need)
        return key

    def record_outcome(self, *, status: str, usage: dict | None) -> dict:
        if self._open is None:
            raise RuntimeError("no open reservation")
        key, reserved = self._open
        verdict = self.assess(usage)
        self.journal.append(
            "spend_reconciled",
            scope=self.scope,
            key=key,
            status=status,
            reserved_usd=str(reserved),
            usd=str(verdict["usd"]),
            usage_known=verdict["usage_known"],
            overrun=verdict["overrun"],
        )
        self._open = None
        return verdict


class StudyCoordinator:
    """Fixed §8.1 schedule + global no-replay over one journal. Does not run arms."""

    def __init__(self, journal: DurableJournal):
        self.journal = journal

    @staticmethod
    def schedule():
        for stage, blocks in STAGES.items():
            for block in blocks:
                for arm in ARM_ORDER:
                    yield stage, block, arm

    def started(self):
        return {
            (e["block"], e["arm"])
            for e in self.journal.read_events()
            if e.get("kind") == "arm_started"
        }

    def finished(self):
        return {
            (e["block"], e["arm"])
            for e in self.journal.read_events()
            if e.get("kind") == "arm_closed"
        }

    def next_unit(self):
        """First scheduled (stage, block, arm) never started. Started-but-unfinished
        units are NOT returned: they are forfeited under the no-replay rule."""
        started = self.started()
        for stage, block, arm in self.schedule():
            if (block, arm) not in started:
                return stage, block, arm
        return None

    def begin(self, block: int, arm: str) -> None:
        if (block, arm) in self.started():
            raise ReplayRefused(f"block {block} arm {arm} already started")
        expected = self.next_unit()
        if expected is None or (expected[1], expected[2]) != (block, arm):
            raise ReplayRefused(f"out of schedule order: expected {expected}, got {(block, arm)}")
        self.journal.append("arm_started", block=block, arm=arm, stage=1 if block < 20 else 2)

    def close(self, block: int, arm: str, *, reason: str) -> None:
        if (block, arm) not in self.started():
            raise ReplayRefused("cannot close an arm that never started")
        if (block, arm) in self.finished():
            raise ReplayRefused("arm already closed")
        self.journal.append("arm_closed", block=block, arm=arm, reason=reason)

    def abandoned(self):
        """Started but never closed (crash): forfeited, never resumed."""
        return sorted(self.started() - self.finished())

    def status(self) -> dict:
        return {
            "scheduled_units": 120,
            "started": len(self.started()),
            "closed": len(self.finished()),
            "abandoned_no_replay": [list(x) for x in self.abandoned()],
            "next": self.next_unit(),
        }


def normative_schedule_from_protocol(protocol_path) -> list[tuple[int, int, str]]:
    """Derive the schedule from the protocol TEXT (§8.1), independent of ARM_ORDER.

    Used by regression tests so the implementation constant is checked against
    the normative document rather than against itself.
    """
    text = Path(protocol_path).read_text()
    section = text.split("### 8.1 Blocks", 1)[1].split("### 8.2", 1)[0]
    s1 = re.search(r"Stage 1:\*\* blocks s = (\d+) … (\d+)", section)
    s2 = re.search(r"Stage 2 \(independent replication\):\*\* blocks s = (\d+) … (\d+)", section)
    order = re.search(r"fixed order ([A-Za-z\-]+) → ([A-Za-z\-]+) → ([A-Za-z\-]+)", section)
    if not (s1 and s2 and order):
        raise ValueError("could not parse §8.1")
    label = {"RS": "RS", "CMA-ES": "CMA", "LLM": "AI"}
    arms = [label[x] for x in order.groups()]
    out = []
    for stage, match in ((1, s1), (2, s2)):
        for block in range(int(match.group(1)), int(match.group(2)) + 1):
            for arm in arms:
                out.append((stage, block, arm))
    return out
