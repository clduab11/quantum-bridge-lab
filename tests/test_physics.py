"""Analytic component identities and synthetic arithmetic; no study objective."""

import importlib
import importlib.util

import numpy as np
import pytest


@pytest.fixture
def physics():
    assert importlib.util.find_spec("qbridge.physics") is not None, "physics component is missing"
    return importlib.import_module("qbridge.physics")


IDENTITY = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.diag([1, -1]).astype(complex)


def test_zero_generator_and_zero_duration_are_identity(physics):
    np.testing.assert_array_equal(physics.segment_unitary([0, 0, 0], 1.7), IDENTITY)
    np.testing.assert_array_equal(physics.segment_unitary([1, 2, 3], 0), IDENTITY)


def test_x_pi_rotation_has_correct_angle_and_sign(physics):
    np.testing.assert_allclose(physics.segment_unitary([1, 0, 0], np.pi), -1j * X, atol=1e-15)


@pytest.mark.parametrize(
    "a,dt",
    [
        ([0.3, -0.7, 0.2], 0.9),
        ([0, 0, 2], -0.4),
        ([1e-200, -1e-200, 0], 1.1),
        ([0, 1, 0], np.pi),
    ],
)
def test_segment_matches_independent_matrix_exponential_and_is_unitary(physics, a, dt):
    from scipy.linalg import expm

    actual = physics.segment_unitary(a, dt)
    reference = expm(-0.5j * dt * (a[0] * X + a[1] * Y + a[2] * Z))
    np.testing.assert_allclose(actual, reference, atol=1e-15, rtol=1e-14)
    np.testing.assert_allclose(actual.conj().T @ actual, IDENTITY, atol=1e-15)


def test_segment_composition_and_subnormal_limit(physics):
    a = [0.25, -0.5, 0.75]
    np.testing.assert_allclose(
        physics.segment_unitary(a, 1.3),
        physics.segment_unitary(a, 0.8) @ physics.segment_unitary(a, 0.5),
        atol=1e-15,
    )
    tiny = np.nextafter(0.0, 1.0)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        np.testing.assert_allclose(
            physics.segment_unitary([tiny, tiny, tiny], 1), IDENTITY, atol=1e-15
        )


def test_representable_rotation_survives_extreme_scale_and_tiny_duration(physics):
    tiny = np.nextafter(0.0, 1.0)
    actual = physics.segment_unitary([1e300, 0, 0], tiny)
    np.testing.assert_allclose(actual[0, 1], -2.4703282292062327e-24j, atol=0, rtol=1e-15)


def test_fidelity_identities_and_global_phase(physics):
    u = physics.segment_unitary([0.2, -0.4, 0.8], 0.7)
    assert physics.process_fidelity(u, u) == pytest.approx(1, abs=1e-15)
    assert physics.process_fidelity(u, np.exp(0.37j) * u) == pytest.approx(1, abs=1e-15)
    assert physics.process_fidelity(IDENTITY, X) == 0
    assert physics.process_fidelity(IDENTITY, (IDENTITY - 1j * X) / np.sqrt(2)) == pytest.approx(
        0.5
    )


def test_average_gate_conversion_matches_six_axial_state_average(physics):
    u = physics.segment_unitary([0.2, -0.4, 0.8], 0.7)
    states = [np.array([1, 0]), np.array([0, 1])]
    states += [np.array([1, phase]) / np.sqrt(2) for phase in [1, -1, 1j, -1j]]
    state_average = np.mean([abs(state.conj() @ u @ state) ** 2 for state in states])
    assert (2 * physics.process_fidelity(IDENTITY, u) + 1) / 3 == pytest.approx(
        state_average, abs=1e-15
    )


def test_synthetic_mean_is_literal_arithmetic_without_clipping(physics):
    assert physics.mean_infidelity([0.25, 0.75]) == 0.5
    assert physics.mean_infidelity([0, 0, 0]) == 1
    assert physics.mean_infidelity([1, 1]) == 0
    overshoot = np.nextafter(1.0, 2.0)
    assert physics.mean_infidelity([overshoot]) == 1 - overshoot
    assert physics.mean_infidelity([overshoot, 0.5]) == 1 - (overshoot + 0.5) / 2


def test_mapping_extremes_boundary_order_and_idempotence(physics):
    maximum = np.finfo(np.float64).max
    tiny = np.nextafter(0.0, 1.0)
    raw = np.array(
        [
            [0, 0],
            [3, 4],
            [-3, 4],
            [maximum, maximum],
            [-maximum, maximum],
            [tiny, -tiny],
            [1, tiny],
            [np.nextafter(1.0, 2.0), 0],
            [0.6, 0.8],
            [1e300, -1e300],
        ]
    )
    original = raw.copy()
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        mapped = physics.map_action(raw.ravel())
    assert mapped.shape == (20,)
    assert mapped.dtype == np.float64
    assert np.all(np.isfinite(mapped))
    np.testing.assert_array_equal(raw, original)
    expected = np.array(
        [
            [0, 0],
            [0.6, 0.8],
            [-0.6, 0.8],
            [1 / np.sqrt(2), 1 / np.sqrt(2)],
            [-1 / np.sqrt(2), 1 / np.sqrt(2)],
            [tiny, -tiny],
            [1, tiny],
            [1, 0],
            [0.6, 0.8],
            [1 / np.sqrt(2), -1 / np.sqrt(2)],
        ]
    )
    np.testing.assert_allclose(mapped.reshape(10, 2), expected, atol=4e-16, rtol=0)
    np.testing.assert_array_equal(mapped[10:14], expected.ravel()[10:14])
    norms = np.hypot(mapped[::2], mapped[1::2])
    assert np.all(norms <= 1 + 16 * 2**-52)
    assert np.max(np.abs(physics.map_action(mapped) - mapped)) <= 16 * 2**-52


def test_mapping_preserves_and_logs_within_tolerance_overshoot(physics, caplog):
    with caplog.at_level("INFO", logger="qbridge.physics"):
        mapped = physics.map_action([21.0, 13.0] + [0.0] * 18)
    np.testing.assert_array_equal(mapped[:2], [0.8502651466878619, 0.5263546146162955])
    assert np.hypot(*mapped[:2]) > 1
    assert np.hypot(*mapped[:2]) <= 1 + physics.TAU_MAP
    assert "mapping_norm_overshoot" in caplog.text


def test_mapping_projects_pair_outside_disk_with_each_coordinate_below_one(physics):
    mapped = physics.map_action([0.9, -0.9] + [0] * 18)
    np.testing.assert_allclose(mapped[:2], [1 / np.sqrt(2), -1 / np.sqrt(2)], atol=2e-16)


@pytest.mark.parametrize(
    "raw",
    [
        [0] * 19,
        [0] * 21,
        [[0, 0]] * 10,
        [False] + [0] * 19,
        [np.bool_(True)] + [0] * 19,
        ["0"] + [0] * 19,
        [None] + [0] * 19,
        [1j] + [0] * 19,
        [10**400] + [0] * 19,
        *([value] + [0] * 19 for value in [np.nan, np.inf, -np.inf]),
    ],
)
def test_mapping_rejects_invalid_raw_domain(physics, raw):
    with pytest.raises(ValueError):
        physics.map_action(raw)


@pytest.mark.parametrize(
    "a,dt",
    [
        ([0, 0], 1),
        ([[0, 0, 0]], 1),
        ([True, 0, 0], 1),
        ([np.inf, 0, 0], 1),
        (["1", 0, 0], 1),
        ([0, 0, 0], True),
        ([0, 0, 0], np.nan),
        ([0, 0, 0], "1"),
    ],
)
def test_segment_rejects_invalid_numeric_inputs(physics, a, dt):
    with pytest.raises(ValueError):
        physics.segment_unitary(a, dt)


def test_segment_rejects_unrepresentable_angle_instead_of_returning_nan(physics):
    with pytest.raises(ValueError, match="rotation angle"):
        physics.segment_unitary([np.finfo(float).max] * 3, np.finfo(float).max)


@pytest.mark.parametrize(
    "matrix",
    [
        np.eye(3),
        [[True, 0], [0, 1]],
        [[np.nan, 0], [0, 1]],
        [[1, 0], [0, np.inf * 1j]],
        [["1", 0], [0, 1]],
    ],
)
def test_fidelity_rejects_invalid_matrices_in_either_argument(physics, matrix):
    with pytest.raises(ValueError):
        physics.process_fidelity(matrix, IDENTITY)
    with pytest.raises(ValueError):
        physics.process_fidelity(IDENTITY, matrix)


@pytest.mark.parametrize(
    "values", [[], [[0.25, 0.75]], [True], ["0.5"], [None], [np.nan], [np.inf], [1j]]
)
def test_aggregation_rejects_empty_nonvector_and_invalid_values(physics, values):
    with pytest.raises(ValueError):
        physics.mean_infidelity(values)
