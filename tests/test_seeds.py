"""Only draws control parameters; never evaluates an objective."""

import importlib

import numpy as np
import pytest


def api():
    return importlib.import_module("qbridge.seeds")


def test_initialization_is_identical_across_arms_without_shared_mutable_streams():
    first = api().initial_batch(0)
    _ = list(api().random_actions(0, count=190))
    second = api().initial_batch(0)
    assert np.array_equal(first, second)
    assert np.asarray(first).shape == (10, 20)
    assert np.all(np.hypot(np.asarray(first)[:, ::2], np.asarray(first)[:, 1::2]) <= 1)
    assert not np.array_equal(first, api().initial_batch(20))


def test_random_search_uses_child_one_and_angle_before_radius():
    child = np.random.SeedSequence(20260908, spawn_key=(3,)).spawn(3)[1]
    source = np.random.Generator(np.random.PCG64(child))
    angle = source.uniform(0.0, 2.0 * np.pi)
    radius = np.sqrt(source.uniform(0.0, 1.0))
    expected = [radius * np.cos(angle), radius * np.sin(angle)]
    actual = next(api().random_actions(3, count=1))
    assert np.array_equal(actual[:2], expected)


def test_cma_seed_is_reproducible_nonzero_and_manifest_names_exact_call():
    module = api()
    manifest = module.seed_manifest(5)
    child = np.random.SeedSequence(20260908, spawn_key=(5,)).spawn(3)[2]
    expected = int(np.random.Generator(np.random.PCG64(child)).integers(1, 2**31))
    assert manifest["cma_seed"] == expected
    assert 1 <= expected <= 2**31 - 1
    assert manifest["generator"] == "PCG64"
    assert manifest["llm_seed_sent"] is False
    assert module.seed_manifest(5) == manifest


@pytest.mark.parametrize("block", [-1, 40, True, 0.5])
def test_invalid_study_block_is_rejected(block):
    with pytest.raises((ValueError, TypeError)):
        api().initial_batch(block)
