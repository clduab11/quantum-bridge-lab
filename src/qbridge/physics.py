"""Protocol v0.4 numerical components; deliberately no study-objective evaluator.

Fidelity and aggregation return their literal formulas without clipping. The
runner owns validation of a final objective and recording simulator invalidity.
"""

import logging
import math
from numbers import Complex, Real

import numpy as np

TAU_MAP = 16 * 2**-52
_LOGGER = logging.getLogger(__name__)
_IDENTITY = np.eye(2, dtype=np.complex128)
_PAULIS = np.array([[[0, 1], [1, 0]], [[0, -1j], [1j, 0]], [[1, 0], [0, -1]]], dtype=np.complex128)


def _numeric_array(values, *, name, complex_values=False):
    """Reject coercible strings and booleans before float/complex conversion."""
    try:
        unconverted = np.asarray(values, dtype=object)
        numeric_type = Complex if complex_values else Real
        if any(
            isinstance(value, (bool, np.bool_)) or not isinstance(value, numeric_type)
            for value in unconverted.flat
        ):
            raise ValueError(f"{name} must contain numbers, excluding booleans")
        dtype = np.complex128 if complex_values else np.float64
        with np.errstate(over="raise", invalid="raise"):
            result = np.asarray(unconverted, dtype=dtype)
    except (TypeError, OverflowError, FloatingPointError) as exc:
        raise ValueError(f"{name} must contain finite representable numbers") from exc
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain finite numbers")
    return result


def map_action(raw) -> np.ndarray:
    """Map exactly 20 finite real coordinates to ten disks per protocol §4.2.

    Returns a fresh float64 vector. Within-TAU_MAP norm overshoots are retained
    unchanged and emitted as INFO log records; a caller can capture these in its
    engineering journal. A failed output check raises ValueError for the runner
    to classify as simulator-invalid, never silently remaps an output.
    """
    values = _numeric_array(raw, name="raw action")
    if values.shape != (20,):
        raise ValueError("raw action must be a vector of exactly 20 coordinates")
    mapped = values.copy()
    for segment, pair in enumerate(mapped.reshape(10, 2)):
        x, y = float(pair[0]), float(pair[1])
        scale = max(abs(x), abs(y))
        if scale == 0:
            pair[:] = 0.0
        elif scale > 1:
            v, w = x / scale, y / scale
            h = math.sqrt(v * v + w * w)
            pair[:] = v / h, w / h
        else:
            h = float(np.hypot(x, y))
            if h > 1:
                pair[:] = x / h, y / h
        norm = float(np.hypot(pair[0], pair[1]))
        if not np.all(np.isfinite(pair)) or not math.isfinite(norm) or norm > 1 + TAU_MAP:
            raise ValueError(f"mapped segment {segment} violates the declared disk tolerance")
        if norm > 1:
            _LOGGER.info(
                "mapping_norm_overshoot segment=%d norm=%r tau_map=%r mapped=%r",
                segment,
                norm,
                TAU_MAP,
                pair.tolist(),
            )
    return mapped


def segment_unitary(a, dt) -> np.ndarray:
    """Return exp(-i dt a·sigma/2) for one finite real three-vector.

    A zero generator or duration gives exact identity. Scaled direction avoids
    division by a vanishing norm. Unrepresentable rotation angles raise
    ValueError rather than return NaNs. Negative time is mathematically allowed.
    """
    vector = _numeric_array(a, name="generator")
    duration = _numeric_array(dt, name="duration")
    if vector.shape != (3,) or duration.shape != ():
        raise ValueError("generator must have three coordinates and duration must be scalar")
    time = float(duration)
    scale = float(np.max(np.abs(vector)))
    if scale == 0 or time == 0:
        return _IDENTITY.copy()
    scaled = vector / scale
    scaled_norm = math.hypot(*scaled)
    # Combine exponents before rounding: halving a subnormal time first would
    # discard a representable angle when the generator scale is large.
    scale_mantissa, scale_exponent = math.frexp(scale)
    time_mantissa, time_exponent = math.frexp(time)
    try:
        angle = math.ldexp(
            scale_mantissa * time_mantissa * scaled_norm,
            scale_exponent + time_exponent - 1,
        )
    except OverflowError as exc:
        raise ValueError("rotation angle is not representable as finite float64") from exc
    direction = scaled / scaled_norm
    generator = np.tensordot(direction, _PAULIS, axes=1)
    return math.cos(angle) * _IDENTITY - 1j * math.sin(angle) * generator


def process_fidelity(target, actual) -> float:
    """Return |Tr(target† actual)/2|² without clipping; caller supplies unitaries."""
    target_matrix = _numeric_array(target, name="target", complex_values=True)
    actual_matrix = _numeric_array(actual, name="actual", complex_values=True)
    if target_matrix.shape != (2, 2) or actual_matrix.shape != (2, 2):
        raise ValueError("target and actual must each have shape (2, 2)")
    return float(abs(np.trace(target_matrix.conj().T @ actual_matrix) / 2) ** 2)


def mean_infidelity(fidelities) -> float:
    """Return literal 1-mean for a nonempty finite vector, including roundoff overshoot.

    This aggregation utility creates no Hamiltonian, target or noise-grid
    objective. Range validation of the final result belongs to the runner.
    """
    values = _numeric_array(fidelities, name="fidelities")
    if values.ndim != 1 or values.size == 0:
        raise ValueError("fidelities must be a nonempty vector")
    return float(1 - np.mean(values))
