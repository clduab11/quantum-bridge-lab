"""Fixed E9 stopping rules. None of these values may be tuned from observations."""

from __future__ import annotations

from dataclasses import dataclass

from counted_responses_provider import contract as C

# The E9 records are a separate journal outside Git. ``E9_ARM`` is a record
# label for that journal only; no study arm (RS, CMA, AI) is constructed and no
# study slot is consumed. See A1.11 and the work order: "do not consume study
# slots or create a study arm merely to reuse its machinery".
E9_ARM = "E9"
E9_BLOCK = 0
STUDY_ARM_LABELS = ("RS", "CMA", "AI")

# A1.11: "<= 12 count and <= 12 generation attempts in total; monotonic stop
# limit 7,400 s (the nominal fixed-backoff HTTP allowance 24x300 + 8x25 ...)".
NOMINAL_HTTP_ALLOWANCE_S = 24 * C.ATTEMPT_TIMEOUT_S + 8 * 25  # 7400


@dataclass(frozen=True)
class E9Limits:
    """Stopping rules, not promises. Overhead and server waits consume the deadline."""

    deadline_seconds: int = NOMINAL_HTTP_ALLOWANCE_S
    max_count_attempts: int = 12
    max_generation_attempts: int = 12
    attempt_timeout_seconds: int = C.ATTEMPT_TIMEOUT_S
    max_attempts_per_logical: int = 3
    admission_limit: int = 272000
    max_output_tokens: int = C.MAX_OUTPUT_TOKENS
    model: str = C.MODEL
    reasoning_effort: str = "medium"

    def __post_init__(self):
        for name in (
            "deadline_seconds",
            "max_count_attempts",
            "max_generation_attempts",
            "attempt_timeout_seconds",
            "max_attempts_per_logical",
            "admission_limit",
            "max_output_tokens",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive int")
        if self.model != C.MODEL:
            raise ValueError("model must be exactly gpt-5.6-sol (no routing alias)")
        if self.reasoning_effort not in C.SUPPORTED_EFFORTS:
            raise ValueError("reasoning_effort must be one documented Sol value")
        if self.max_output_tokens != C.MAX_OUTPUT_TOKENS:
            raise ValueError("max_output_tokens must be the int 8192")
        if self.admission_limit > 272000:
            raise ValueError("admission limit must not exceed the prospective L* = 272000")
        if self.attempt_timeout_seconds != C.ATTEMPT_TIMEOUT_S:
            raise ValueError("attempt timeout is fixed at the reviewed 300 s")
        # 4 fixtures x 3 attempts per class is exactly the A1.11 allowance.
        if self.max_count_attempts > 12 or self.max_generation_attempts > 12:
            raise ValueError("E9 allows at most 12 attempts of each class in total")
        if self.max_attempts_per_logical > 3:
            raise ValueError("retry_decision permits attempt numbers 1..3 only")
