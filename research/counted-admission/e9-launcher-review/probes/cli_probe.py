"""Observe the documented default and credential isolation with fabricated data."""

import json
import os
import tempfile
from types import SimpleNamespace

from e9tests import support
from qbridge_e9 import cli


def main():
    output = {}
    try:
        cli.main([])
    except Exception as exc:
        output["default_invocation"] = {
            "exception": type(exc).__name__,
            "message": str(exc),
        }

    reads = []

    class FakeEnvironment(dict):
        def get(self, key, default=None):
            if key == "OPENAI_API_KEY":
                reads.append(key)
            return super().get(key, default)

    original_environment = os.environ
    os.environ = FakeEnvironment(
        {"OPENAI_API_KEY": "FABRICATED-probe-key-not-a-real-secret"}
    )
    try:
        args = SimpleNamespace(
            work_dir=tempfile.mkdtemp(prefix="cli-probe-"),
            effort="medium",
            authority=None,
            usd_ceiling="25",
            count_fee_ceiling="1.088",
            recorded_at=support.RECORDED,
            valid_through=support.VALID_THROUGH,
            fixtures=support.FIXTURES_DIR,
            repo_root=support.REPO_ROOT,
            adoption_evidence=None,
            billing_evidence=None,
            authorization=None,
            specification=None,
        )
        report, _ = cli.run_mode(args, "dry-run")
        output["dry_run"] = {
            "key_get_count": len(reads),
            "accepted": report["acceptance"]["e9_accepted"],
            "fabricated": report["fabricated_responses"],
        }
    finally:
        os.environ = original_environment
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
