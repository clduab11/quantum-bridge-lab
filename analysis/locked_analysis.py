"""Locked endpoint-only analysis CLI; no experimental runner or provider calls.

Input is exactly {"rows": [...], "svf": bool, "ivf": bool}. The output hash must
subsequently be committed to the public manifest before custody selection.
"""

import argparse
from pathlib import Path

from qbridge.analysis import analyze_masked
from qbridge.custody import read_json_bytes, seal_output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    payload = read_json_bytes(args.input.read_bytes())
    if not isinstance(payload, dict) or set(payload) != {"rows", "svf", "ivf"}:
        raise ValueError("input requires exactly rows, svf and ivf")
    output = analyze_masked(payload["rows"], svf=payload["svf"], ivf=payload["ivf"])
    print(seal_output(output, args.output))


if __name__ == "__main__":
    main()
