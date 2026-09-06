"""Tests for the topology and four-attractor oracle calculations."""

import math

from tarot_engine import (
    calculate_branch_probabilities,
    calculate_gravity_gradient,
    calculate_knot_topology,
)


def test_knot_topology_returns_finite_frenet_values():
    topology = calculate_knot_topology([100.0, 100.2, 99.8, 100.4, 100.1])

    assert math.isfinite(topology["kappa"])
    assert math.isfinite(topology["tau"])
    assert topology["kappa"] >= 0.0


def test_gravity_gradient_follows_order_book_imbalance():
    assert calculate_gravity_gradient({"bid_volume": 3.0, "ask_volume": 1.0}) > 0.0
    assert calculate_gravity_gradient({"bid_volume": 1.0, "ask_volume": 3.0}) < 0.0


def test_branch_probabilities_sum_to_one_hundred():
    branches = calculate_branch_probabilities(0.45, -0.12, 1.5)

    assert [branch["id"] for branch in branches] == ["wands", "swords", "cups", "pentacles"]
    assert [branch["color_hex"] for branch in branches] == ["#FFD700", "#00FFFF", "#FFFFFF", "#800080"]
    assert round(sum(float(branch["prob"]) for branch in branches), 1) == 100.0
