"""Observe a direct-orchestrator counterexample using fabricated responses only.

The CLI's full-allowance gate rejects this deliberately small authority. This
probe does not demonstrate an overspend through that gate or with patch 0002.
"""

import argparse
import json
import tempfile
from pathlib import Path

from counted_responses_provider import contract as C
from e9tests import support
from qbridge_e9 import mocks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("original", "patched"), required=True)
    args = parser.parse_args()
    patched = hasattr(C, "worst_case_input_rate")
    assert patched == (args.variant == "patched")
    ceiling = "2.60368"
    authority = support.authority(usd_ceiling=ceiling, count_fee_ceiling_usd="0")
    handler = mocks.ScriptedTransport(
        [lambda request: mocks.count_response(272000)],
        [
            lambda request: mocks.error_response(500),
            lambda request: mocks.generation_response(
                counted_tokens=272000, output_tokens=8192, cache_write=272000
            ),
        ],
    )
    with tempfile.TemporaryDirectory(prefix="qbridge-money-retry-") as directory:
        journal, provider, _records, orchestrator, _clock, _fixtures = support.build(
            Path(directory), handler, auth=authority
        )
        try:
            outcomes = orchestrator.run()
            result = {
                "patched2": patched,
                "wire_generations": len(handler.generation_calls),
                "ceiling_usd": ceiling,
                "committed_usd": C.money_str(provider.ledger.state()["committed"]),
                "stop": orchestrator._stop_reason,
                "outcome0": outcomes[0].outcome,
                "all_activity_offline": True,
                "scope": (
                    "Direct synthetic orchestrator; the CLI gate rejects this low "
                    "full-allowance authority before dispatch."
                ),
            }
            assert result["wire_generations"] == (1 if patched else 2)
            assert result["committed_usd"] == ("1.523840" if patched else "2.775680")
            if patched:
                assert result["stop"] == "monetary_ceiling_reached"
            else:
                assert result["stop"] == "e9_fail:cache_activity:cache_write_tokens=272000"
        finally:
            journal.close()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
