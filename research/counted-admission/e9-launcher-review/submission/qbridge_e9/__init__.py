"""Bounded E9 model-preflight launcher.

E9 is the single permitted pre-freeze provider exercise described in protocol
amendment A1 (proposed) section A1.11/§11. This package supplies the execution
entry point that was listed as remaining work in
``research/counted-admission/STATUS.md``: it sequences the four fixed fixtures
through the reviewed single-attempt Responses provider, owns the attempt caps,
retry rule and monotonic stop limit, evaluates the A1 acceptance conditions and
writes a durable report.

Nothing in this package adopts amendment A1, freezes protocol v0.4, authorizes
money or launches the study. The default mode is an offline dry run against
``httpx.MockTransport`` with fabricated responses. A live dispatch additionally
requires every requirement in :mod:`qbridge_e9.gate` to pass; unresolved
requirements are recorded as failures, never as defaults.
"""

from qbridge_e9.limits import E9Limits, E9_ARM, E9_BLOCK

__all__ = ["E9Limits", "E9_ARM", "E9_BLOCK"]
