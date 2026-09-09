"""Executable E9 launcher. The offline dry run is the default MODE, but there
is no default COMMAND: an invocation with no subcommand is a clean usage error.

    # 1. verify the committed fixtures only (no journal, no provider)
    python -m qbridge_e9.cli verify-fixtures --fixtures <dir> --repo-root <dir>

    # 2. evaluate the live gate without running anything
    python -m qbridge_e9.cli gate --fixtures <dir> --repo-root <dir> \
        --work-dir <dir> [--check-credential]

    # 3. FULL offline dry run: fabricated responses, no key, no network,
    #    complete orchestration and a timestamped report
    python -m qbridge_e9.cli dry-run --fixtures <dir> --repo-root <dir> \
        --work-dir <dir>

    # 4. future gated live run: refuses unless every gate requirement passes
    python -m qbridge_e9.cli live --fixtures <dir> --repo-root <dir> \
        --work-dir <dir> --authority <file> --adoption-evidence <file> \
        --billing-evidence <file> --authorization <file> \
        --specification <file> --confirm-live

Review findings fixed here:

* **3** - ``RequestRecords`` is now constructed with the VERIFIED repository
  root as ``public_repo``, not a fabricated sibling path, so its
  outside-the-repository check is real.
* **8** - no offline path reads ``OPENAI_API_KEY``. The dry run passes an empty
  environment to the gate; the ``gate`` subcommand reads credential presence
  only when ``--check-credential`` is given. A bare invocation prints usage and
  exits 2 instead of raising ``AttributeError``.

A synthetic authority cannot dispatch live and a real authority cannot run
against the mock transport: the provider refuses both pairings at the wire
boundary (``provider._preflight`` / ``_boundary_recheck``).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import time
from pathlib import Path

from counted_responses_provider.authority import (
    HTTPX_VERSION,
    SDK_VERSION,
    AuthorityRecord,
    profile_sha256,
)
from counted_responses_provider.provider import SingleAttemptResponsesProvider
from qbridge.journal import DurableJournal
from qbridge.request_records import RequestRecords

from qbridge_e9 import mocks
from qbridge_e9.acceptance import evaluate_acceptance
from qbridge_e9.deadline import DeadlineGuard, guarded_transport_factory
from qbridge_e9.fixtures import load_fixture_set
from qbridge_e9.gate import API_KEY_ENV, GateFailed, evaluate_gate, git_worktree_root
from qbridge_e9.limits import E9Limits
from qbridge_e9.orchestrator import E9Orchestrator
from qbridge_e9.report import build_report, write_report

FABRICATED_KEY = "sk-OFFLINE-FABRICATED-NEVER-VALID"
# Documented promotional rates for gpt-5.6-sol, short context (<= 272,000 input
# tokens), USD per 1M tokens, from developers.openai.com/api/docs/models/
# gpt-5.6-sol.md and .../api/docs/pricing.md retrieved 2026-09-09. Used for the
# dry run's arithmetic only; a live run must supply a retained, hashed source.
DOC_RATES = {
    "input_usd_per_million": "4",
    "cached_input_usd_per_million": "0.4",
    "cache_write_usd_per_million": "5",
    "output_usd_per_million": "20",
}
# The conservative worst case for 12 generation attempts at the admission limit
# plus 12 count attempts at the dry run's assumed per-attempt count ceiling.
# UNAPPROVED: this is the dry run's arithmetic, not an authorization.
DRY_RUN_CEILING = "32"


def private_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, stat.S_IRWXU)
    return path


def synthetic_authority(*, usd_ceiling, count_fee_ceiling_usd, limits, recorded, valid_through):
    """A FABRICATED authority for offline runs. Not an authorization.

    ``synthetic=True`` binds this record to ``httpx.MockTransport``: the provider
    refuses it against any real transport, so it cannot dispatch live.
    """
    placeholder = hashlib.sha256(
        b"FABRICATED offline placeholder; not evidence of any rate or fee"
    ).hexdigest()
    return AuthorityRecord(
        scope="e9",
        synthetic=True,
        authorized_by="FABRICATED offline dry run; this is NOT an authorization",
        recorded_at_utc=recorded,
        purpose="offline E9 orchestration dry run against httpx.MockTransport",
        profile_sha256=profile_sha256(limits.reasoning_effort),
        model=limits.model,
        reasoning_effort=limits.reasoning_effort,
        input_token_ceiling=limits.admission_limit,
        max_output_tokens=limits.max_output_tokens,
        count_attempt_cap=limits.max_count_attempts,
        generation_attempt_cap=limits.max_generation_attempts,
        usd_ceiling=usd_ceiling,
        billing_categories=("input", "cached_input", "cache_write", "output"),
        rate_source="FABRICATED placeholder for the retained gpt-5.6-sol rate page",
        rate_source_sha256=placeholder,
        price_valid_through_utc=valid_through,
        count_fee_ceiling_usd=count_fee_ceiling_usd,
        count_fee_evidence=(
            "FABRICATED placeholder; NO count-request fee evidence exists. A real"
            " run requires account or provider contract evidence covering failed"
            " and rejected count attempts."
        ),
        count_fee_evidence_sha256=placeholder,
        count_fee_valid_through_utc=valid_through,
        count_fee_covers_failed_and_rejected=True,
        count_fee_verified=True,
        sdk_version=SDK_VERSION,
        httpx_version=HTTPX_VERSION,
        **DOC_RATES,
    )


def _common(parser):
    parser.add_argument("--fixtures", required=True, help="committed e9-inputs directory")
    parser.add_argument(
        "--repo-root",
        required=True,
        help="pinned checkout; the reviewed source set is verified against it and the"
        " records directory must lie outside it",
    )
    parser.add_argument("--work-dir", required=True, help="private directory OUTSIDE Git")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--usd-ceiling", default=DRY_RUN_CEILING,
                        help="E9-only USD ceiling (UNAPPROVED scenario figure)")
    parser.add_argument("--count-fee-ceiling", default="1.088",
                        help="ASSUMED USD ceiling for ONE count attempt incl. failed/rejected;"
                        " no count fee has been established")
    parser.add_argument("--recorded-at", default="2026-09-09T00:00:00Z")
    parser.add_argument("--valid-through", default="2026-11-21T00:00:00Z")
    parser.add_argument("--authority", default=None)
    parser.add_argument("--adoption-evidence", default=None)
    parser.add_argument("--billing-evidence", default=None)
    parser.add_argument("--authorization", default=None)
    parser.add_argument("--specification", default=None)


def _setup(args, mode):
    # Review finding 3: refuse BEFORE creating anything if the work directory
    # lies inside a Git worktree. Raw request and response bytes must never be
    # written where they can be committed, in any mode, and there is no
    # override flag.
    intended = Path(args.work_dir)
    probe = intended if intended.exists() else intended.parent
    worktree = git_worktree_root(probe)
    if worktree is not None:
        raise GateFailed(
            f"refusing to write E9 records inside a Git worktree rooted at {worktree}: "
            f"--work-dir {intended} must be a private directory outside any repository"
        )
    work = private_dir(args.work_dir)
    records_dir = private_dir(work / "raw")
    journal_path = work / "e9_journal.jsonl"
    limits = E9Limits(reasoning_effort=args.effort)
    if args.authority:
        authority = AuthorityRecord.load(args.authority)
    else:
        if mode == "live":
            raise GateFailed("a live run requires --authority naming a recorded AuthorityRecord")
        authority = synthetic_authority(
            usd_ceiling=args.usd_ceiling,
            count_fee_ceiling_usd=args.count_fee_ceiling,
            limits=limits,
            recorded=args.recorded_at,
            valid_through=args.valid_through,
        )
    return work, records_dir, journal_path, limits, authority


def _inner_transport_factory(mode, fixture_set):
    import httpx

    if mode == "live":
        return (lambda: httpx.HTTPTransport(retries=0)), "httpx.HTTPTransport"
    scripted, _counts = mocks.nominal_plan(fixture_set)
    return (lambda: httpx.MockTransport(scripted)), "httpx.MockTransport"


def run_mode(args, mode, *, env=None):
    """Run one E9 mode. ``env`` is explicit; offline callers get an empty one."""
    work, records_dir, journal_path, limits, authority = _setup(args, mode)
    fabricated = mode != "live"
    repo_root = Path(args.repo_root).resolve()

    if mode == "live":
        env = os.environ if env is None else env
        api_key = env.get(API_KEY_ENV, "")
        if not str(api_key).strip():
            raise GateFailed(f"{API_KEY_ENV} is absent; refusing a live run")
        gate_env = env
    else:
        # Review finding 8: no offline path reads the credential variable.
        api_key = FABRICATED_KEY
        gate_env = {}

    with DurableJournal(journal_path) as journal:
        # Review finding 3: the real verified repository root, not a stub path.
        records = RequestRecords(records_dir, public_repo=repo_root)
        fixture_set = load_fixture_set(
            args.fixtures, reasoning_effort=limits.reasoning_effort, repo_root=repo_root
        )
        inner_factory, transport_class = _inner_transport_factory(mode, fixture_set)
        guard = DeadlineGuard()
        provider = SingleAttemptResponsesProvider(
            journal=journal,
            records=records,
            authority=authority,
            transport_factory=guarded_transport_factory(inner_factory, guard),
            api_key_provider=lambda: api_key,
            wall_clock=time.time,
        )
        # Re-verify the committed bytes against the provider's own prepare step.
        fixture_set = load_fixture_set(
            args.fixtures,
            reasoning_effort=limits.reasoning_effort,
            provider=provider,
            repo_root=repo_root,
        )

        gate = evaluate_gate(
            mode=mode,
            authority=authority,
            limits=limits,
            now_utc=time.time(),
            env=gate_env,
            adoption_evidence=args.adoption_evidence,
            billing_evidence=args.billing_evidence,
            authorization_record=args.authorization,
            specification_path=args.specification,
            records_dir=records_dir,
            repo_root=repo_root,
        )
        journal.append(
            "e9_gate_evaluated",
            mode=mode,
            may_dispatch_live=gate.may_dispatch_live,
            failed_keys=[r.key for r in gate.failures],
            credential_checked=bool(gate_env),
        )
        if mode == "live" and not gate.may_dispatch_live:
            raise GateFailed(
                "live gate failed; unresolved requirements: "
                + ", ".join(r.key for r in gate.failures)
            )

        orchestrator = E9Orchestrator(
            journal=journal,
            provider=provider,
            fixture_set=fixture_set,
            records_dir=records_dir,
            limits=limits,
            deadline_guard=guard,
        )
        started = time.monotonic()
        outcomes = orchestrator.run()
        elapsed = time.monotonic() - started
        acceptance = evaluate_acceptance(
            journal, outcomes, reasoning_effort=limits.reasoning_effort
        )
        report = build_report(
            mode=mode,
            fixture_set=fixture_set,
            gate_result=gate,
            outcomes=outcomes,
            acceptance=acceptance,
            provider=provider,
            journal=journal,
            limits=limits,
            stop_reason=orchestrator._stop_reason,
            elapsed_seconds=elapsed,
            fabricated=fabricated,
            authority=authority,
            records_dir=records_dir,
            journal_path=journal_path,
            orchestrator=orchestrator,
            transport_class=transport_class,
        )
        path = write_report(report, work)
        records.close()
    return report, path


def build_parser():
    parser = argparse.ArgumentParser(
        prog="qbridge_e9.cli", description="Bounded E9 model-preflight launcher"
    )
    sub = parser.add_subparsers(dest="command")

    verify = sub.add_parser("verify-fixtures", help="verify committed fixtures and hashes")
    verify.add_argument("--fixtures", required=True)
    verify.add_argument("--repo-root", required=True)
    verify.add_argument("--effort", default="medium")

    gate_cmd = sub.add_parser("gate", help="evaluate the live gate without running")
    _common(gate_cmd)
    gate_cmd.add_argument(
        "--check-credential",
        action="store_true",
        help=f"read only whether {API_KEY_ENV} is present (never its value); off by default"
        " so no offline invocation touches the credential environment",
    )

    dry = sub.add_parser("dry-run", help="offline dry run with FABRICATED responses")
    _common(dry)

    live = sub.add_parser("live", help="gated live run (requires every requirement to pass)")
    _common(live)
    live.add_argument("--confirm-live", action="store_true",
                      help="required acknowledgement that a live paid dispatch is intended")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        # Review finding 8: a clean, documented usage error - never a silent
        # fall-through into an execution mode with unset arguments.
        parser.print_usage(sys.stderr)
        print(
            "refused: a subcommand is required "
            "(verify-fixtures | gate | dry-run | live). "
            "There is no implicit default; the offline dry run must be asked for.",
            file=sys.stderr,
        )
        return 2

    if args.command == "verify-fixtures":
        fixture_set = load_fixture_set(
            args.fixtures, reasoning_effort=args.effort, repo_root=args.repo_root
        )
        print(json.dumps(fixture_set.as_dict(), indent=2, sort_keys=True))
        return 0 if not fixture_set.failed else 1

    if args.command == "gate":
        try:
            _work, records_dir, _journal, limits, authority = _setup(args, "gate-only")
        except GateFailed as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        env = {}
        if args.check_credential:
            env = {API_KEY_ENV: os.environ.get(API_KEY_ENV, "")}
        gate = evaluate_gate(
            mode="live",
            authority=authority,
            limits=limits,
            now_utc=time.time(),
            env=env,
            adoption_evidence=args.adoption_evidence,
            billing_evidence=args.billing_evidence,
            authorization_record=args.authorization,
            specification_path=args.specification,
            records_dir=records_dir,
            repo_root=Path(args.repo_root).resolve(),
        )
        print(json.dumps(gate.as_dict(), indent=2, sort_keys=True))
        return 0 if gate.may_dispatch_live else 2

    if args.command == "live":
        if not getattr(args, "confirm_live", False):
            print("refused: --confirm-live is required for a live dispatch", file=sys.stderr)
            return 2
        try:
            report, path = run_mode(args, "live")
        except GateFailed as exc:
            print(f"refused: {exc}", file=sys.stderr)
            return 2
        print(json.dumps({"report": str(path), "accepted": report["acceptance"]["e9_accepted"]}))
        return 0 if report["acceptance"]["e9_accepted"] else 1

    try:
        report, path = run_mode(args, "dry-run", env={})
    except GateFailed as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "mode": report["mode"],
                "fabricated_responses": report["fabricated_responses"],
                "report": str(path),
                "fixture_checks_passed": report["fixtures"]["checks_passed"],
                "fixture_checks_failed": report["fixtures"]["checks_failed"],
                "gate_may_dispatch_live": report["gate"]["may_dispatch_live"],
                "gate_failed_keys": report["gate"]["failed_keys"],
                "stop_reason": report["run"]["stop_reason"],
                "attempts": report["ledger"]["attempts"],
                "committed_usd": report["ledger"]["committed_usd"],
                "e9_accepted": report["acceptance"]["e9_accepted"],
                "acceptance_failed": report["acceptance"]["failed_keys"],
            },
            indent=2,
        )
    )
    return 0 if report["acceptance"]["e9_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
