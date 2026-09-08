"""Protocol v0.4 streams; these helpers draw parameters but evaluate nothing."""

from __future__ import annotations

import numpy as np

ENTROPY = 20260908


def _children(block):
    if isinstance(block, bool) or not isinstance(block, int) or not 0 <= block < 40:
        raise ValueError("block must be an integer from 0 through 39")
    return np.random.SeedSequence(ENTROPY, spawn_key=(block,)).spawn(3)


def _draw(generator):
    # Fixed consumption order: vector-major, segment-major, angle then radius.
    vector = []
    for _ in range(10):
        angle = generator.uniform(0.0, 2.0 * np.pi)
        radius = np.sqrt(generator.uniform(0.0, 1.0))
        vector.extend((float(radius * np.cos(angle)), float(radius * np.sin(angle))))
    return vector


def initial_batch(block: int):
    """Recreate the same ten vectors for every arm, without sharing RNG state."""
    generator = np.random.Generator(np.random.PCG64(_children(block)[0]))
    return [_draw(generator) for _ in range(10)]


def random_actions(block: int, *, count: int = 190):
    """Draw RS-only samples from child one; never consumes initialization state."""
    if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 190:
        raise ValueError("count must be an integer from 0 through 190")
    generator = np.random.Generator(np.random.PCG64(_children(block)[1]))
    for _ in range(count):
        yield _draw(generator)


def seed_manifest(block: int):
    child = _children(block)[2]
    generator = np.random.Generator(np.random.PCG64(child))
    seed = int(generator.integers(1, 2**31))
    return {"entropy": ENTROPY, "block": block, "spawn_key": [block],
            "children": {"init": 0, "rs": 1, "cma": 2}, "generator": "PCG64",
            "cma_seed": seed, "cma_seed_call": "int(generator.integers(1, 2**31))",
            "draw_order": "vector, segment, uniform angle, uniform radius-squared",
            "llm_seed_sent": False}
