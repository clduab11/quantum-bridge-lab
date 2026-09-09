"""Durable monetary reservations for the two request classes.

All state lives in the DurableJournal (fork-safe: re-read on every call).
Amounts are exact Fractions serialized as bounded "numerator/denominator"
strings plus a decimal rendering. Journal keys: every event references the
runner's transport reservation as `transport_reservation` and its own id as
`money_reservation`; the top-level `reservation` key is never used here
(it is owned by DurableJournal.reserve/complete).

Outcomes of a reservation (`money_settled.outcome`):
  released_not_dispatched  the wrapped transport was never invoked (no bytes left)
  retained_unknown         dispatch may have happened; billing unknown -> full amount kept
  retained_ceiling         count class: only a verified maximum is known -> kept in full
  retained_unreconciled    usage present but not reconciled -> max(reserved, known
                           category charge) kept; a known charge above the
                           reservation is an overrun (halts) even when the total
                           is contradictory
  settled_actual           reconciled usage; computed charge <= reservation
  overrun_recorded         reconciled usage; computed charge > reservation, recorded
                           UNCLIPPED and the scope halts
A reservation without a settlement event counts at its reserved amount.
Software bounds are conditional on provider compliance; `billing_reconciled`
is always null here because no invoice is ever inspected by this code.
"""

from __future__ import annotations

import re
from fractions import Fraction

from .contract import ContractViolation, money_str

FRACTION_GRAMMAR = r"-?[0-9]{1,80}/[0-9]{1,80}"
RESERVED_KIND = "money_reserved"
SETTLED_KIND = "money_settled"
OUTCOMES = (
    "released_not_dispatched",
    "retained_unknown",
    "retained_ceiling",
    "retained_unreconciled",
    "settled_actual",
    "overrun_recorded",
)
RETAINED = {"retained_unknown", "retained_ceiling", "retained_unreconciled"}


def fraction_to_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise ContractViolation("amount must be a Fraction")
    return f"{value.numerator}/{value.denominator}"


def fraction_from_text(text) -> Fraction:
    if not isinstance(text, str) or not re.fullmatch(FRACTION_GRAMMAR, text):
        raise ContractViolation("amount text outside the bounded fraction grammar")
    numerator, denominator = text.split("/")
    if int(denominator) == 0:
        raise ContractViolation("zero denominator")
    return Fraction(int(numerator), int(denominator))


def decimal_text(value: Fraction) -> str:
    """Exact fixed-point rendering when it terminates within 12 places, else the
    fraction text (never rounded)."""
    try:
        return money_str(value, 12)
    except ContractViolation:
        return fraction_to_text(value)


class LedgerHalted(RuntimeError):
    """A known overrun or ceiling breach is recorded; no further reservation."""


class MoneyLedger:
    def __init__(self, journal, *, scope: str, ceiling: Fraction):
        if scope not in ("e9", "study"):
            raise ValueError("scope must be e9 or study")
        if not isinstance(ceiling, Fraction) or ceiling <= 0:
            raise ValueError("ceiling must be a positive Fraction")
        self.journal = journal
        self.scope = scope
        self.ceiling = ceiling

    # -- durable reads --------------------------------------------------------
    def _events(self):
        return [
            e
            for e in self.journal.read_events()
            if e["kind"] in (RESERVED_KIND, SETTLED_KIND) and e.get("scope") == self.scope
        ]

    def state(self) -> dict:
        reserved = {}
        settled = {}
        for event in self._events():
            if event["kind"] == RESERVED_KIND:
                reserved[event["money_reservation"]] = event
            else:
                settled[event["money_reservation"]] = event
        committed = Fraction(0)
        counts = {"count": 0, "generation": 0}
        unknown = 0
        overrun = False
        for key, event in reserved.items():
            amount = fraction_from_text(event["amount"])
            counts[event["request_class"]] += 1
            outcome = settled.get(key)
            if outcome is None:
                committed += amount
                unknown += 1
                continue
            kind = outcome["outcome"]
            if kind == "released_not_dispatched":
                continue
            if kind in RETAINED:
                # Review fix R1: an unreconciled report must not understate a KNOWN
                # category charge. Book max(reserved, computed) and flag an overrun.
                computed = outcome.get("computed_charge")
                known = None if computed is None else fraction_from_text(computed)
                if known is not None and known > amount:
                    committed += known
                    overrun = True
                else:
                    committed += amount
                unknown += 1
            elif kind == "settled_actual":
                committed += fraction_from_text(outcome["computed_charge"])
            elif kind == "overrun_recorded":
                committed += fraction_from_text(outcome["computed_charge"])
                overrun = True
            else:
                raise ContractViolation(f"unknown settlement outcome {kind!r}")
        return {
            "scope": self.scope,
            "ceiling": self.ceiling,
            "committed": committed,
            "attempts": counts,
            "unresolved_or_retained": unknown,
            "overrun_recorded": overrun,
            "halted": overrun or committed > self.ceiling,
            "open": [k for k in reserved if k not in settled],
        }

    def summary(self) -> dict:
        state = self.state()
        return {
            "scope": state["scope"],
            "ceiling_usd": decimal_text(state["ceiling"]),
            "committed_usd_bound": decimal_text(state["committed"]),
            "attempts": state["attempts"],
            "unresolved_or_retained": state["unresolved_or_retained"],
            "overrun_recorded": state["overrun_recorded"],
            "halted": state["halted"],
            "billing_reconciled": None,
        }

    # -- durable writes -------------------------------------------------------
    def reserve(
        self,
        *,
        request_class: str,
        transport_reservation: str,
        amount: Fraction,
        basis: dict,
        class_cap: int,
    ) -> str:
        if request_class not in ("count", "generation"):
            raise ValueError("request_class must be count or generation")
        if not isinstance(amount, Fraction) or amount < 0:
            raise ContractViolation("reservation amount must be a non-negative Fraction")
        state = self.state()
        if state["halted"]:
            raise LedgerHalted("ledger_halted")
        if state["attempts"][request_class] + 1 > class_cap:
            raise LedgerHalted(f"{request_class}_attempt_cap_reached")
        if state["committed"] + amount > self.ceiling:
            raise LedgerHalted("monetary_ceiling_reached")
        key = f"money:{self.scope}:{request_class}:{transport_reservation}"
        if key in state["open"] or any(e.get("money_reservation") == key for e in self._events()):
            raise LedgerHalted("duplicate_money_reservation")
        self.journal.append(
            RESERVED_KIND,
            scope=self.scope,
            money_reservation=key,
            transport_reservation=transport_reservation,
            request_class=request_class,
            amount=fraction_to_text(amount),
            amount_usd=decimal_text(amount),
            basis=basis,
            committed_before=fraction_to_text(state["committed"]),
        )
        return key

    def settle(
        self,
        money_reservation: str,
        *,
        outcome: str,
        computed_charge: Fraction | None,
        reconciled: bool,
        findings: list,
        usage=None,
    ) -> dict:
        if outcome not in OUTCOMES:
            raise ContractViolation("unknown settlement outcome")
        state = self.state()
        if money_reservation not in state["open"]:
            raise ContractViolation("settlement requires exactly one open reservation")
        reserved = next(
            e
            for e in self._events()
            if e["kind"] == RESERVED_KIND and e["money_reservation"] == money_reservation
        )
        amount = fraction_from_text(reserved["amount"])
        if outcome in ("settled_actual", "overrun_recorded"):
            if not isinstance(computed_charge, Fraction) or computed_charge < 0:
                raise ContractViolation("actual settlement requires a computed charge")
            if not reconciled:
                raise ContractViolation("only reconciled usage may settle to an actual charge")
            if (computed_charge > amount) != (outcome == "overrun_recorded"):
                raise ContractViolation("outcome does not match charge versus reservation")
        if outcome in RETAINED and reconciled and computed_charge is not None:
            raise ContractViolation("a reconciled known charge must settle, not be retained")
        record = self.journal.append(
            SETTLED_KIND,
            scope=self.scope,
            money_reservation=money_reservation,
            transport_reservation=reserved["transport_reservation"],
            request_class=reserved["request_class"],
            outcome=outcome,
            reserved=reserved["amount"],
            computed_charge=None if computed_charge is None else fraction_to_text(computed_charge),
            computed_charge_usd=None if computed_charge is None else decimal_text(computed_charge),
            retained=None if outcome not in RETAINED else reserved["amount"],
            reconciled=bool(reconciled),
            billing_reconciled=None,
            findings=list(findings),
            usage=usage,
        )
        return record
