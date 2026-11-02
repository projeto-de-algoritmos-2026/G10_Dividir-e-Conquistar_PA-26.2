from __future__ import annotations

import math
import random

import pytest

from ranklab.algorithms import (
    SelectionError,
    percentile_to_order,
    select_k,
    select_percentile,
)


def test_select_k_handles_unsorted_values_without_mutating_input() -> None:
    values = [9, 1, 7, 3, 5, 3, 8, 2, 6, 4]
    result = select_k(values, 4)

    assert result.value == 3
    assert result.order == 4
    assert values == [9, 1, 7, 3, 5, 3, 8, 2, 6, 4]


def test_select_k_supports_objects_and_duplicate_keys() -> None:
    items = [{"id": "a", "score": 4}, {"id": "b", "score": 1}, {"id": "c", "score": 4}]

    result = select_k(items, 2, key=lambda item: item["score"])

    assert result.value["score"] == 4


@pytest.mark.parametrize(
    "values",
    [
        [42],
        list(range(20)),
        list(reversed(range(20))),
        [7] * 20,
        [0, 1] * 10,
        [5, -1, 5, -1, 0, 0, 12, -8],
    ],
)
def test_select_k_matches_sorted_oracle_for_adversarial_inputs(
    values: list[int],
) -> None:
    original = values.copy()
    expected = sorted(values)

    for order, expected_value in enumerate(expected, start=1):
        result = select_k(values, order)
        assert result.value == expected_value
        assert result.order == order

    assert values == original


def test_deterministic_small_inputs_match_sorted_oracle() -> None:
    generator = random.Random(2026)

    for size in (1, 2, 5, 6, 17, 50):
        for _ in range(8):
            values = [generator.randint(-size, size) for _ in range(size)]
            expected = sorted(values)

            for order in range(1, size + 1):
                assert select_k(values, order).value == expected[order - 1]


def test_object_selection_matches_sorted_key_oracle() -> None:
    items = [
        {"id": "delta", "score": 4},
        {"id": "alpha", "score": -2},
        {"id": "charlie", "score": 9},
        {"id": "bravo", "score": 1},
    ]
    original = [item.copy() for item in items]

    for order in range(1, len(items) + 1):
        expected = sorted(items, key=lambda item: item["score"])[order - 1]
        result = select_k(items, order, key=lambda item: item["score"])
        assert result.value == expected

    assert items == original


@pytest.mark.parametrize(
    ("percentile", "expected_order"),
    [(0, 1), (1, 1), (50, 2), (51, 3), (100, 4)],
)
def test_percentile_uses_nearest_rank(percentile: float, expected_order: int) -> None:
    assert percentile_to_order(percentile, 4) == expected_order


def test_select_percentile_reports_percentile_and_order() -> None:
    result = select_percentile([40, 10, 30, 20], 50)

    assert result.value == 20
    assert result.order == 2
    assert result.percentile == 50


@pytest.mark.parametrize("percentile", [0, 0.1, 25, 50, 73.5, 99, 100])
def test_percentile_selection_matches_nearest_rank_sorted_oracle(
    percentile: float,
) -> None:
    values = [11, -3, 7, 7, 20, 0, 4]
    expected_order = max(1, math.ceil(percentile * len(values) / 100))

    result = select_percentile(values, percentile)

    assert result.order == expected_order
    assert result.value == sorted(values)[expected_order - 1]
    assert result.percentile == float(percentile)


@pytest.mark.parametrize("operation", ["empty", "bad_k", "bad_percentile"])
def test_selection_rejects_invalid_contract(operation: str) -> None:
    with pytest.raises(SelectionError):
        if operation == "empty":
            select_k([], 1)
        elif operation == "bad_k":
            select_k([1, 2], 0)
        else:
            select_percentile([1, 2], 101)


@pytest.mark.parametrize("bad_k", [-1, 0, 3, True, 1.5, "1"])
def test_select_k_rejects_invalid_orders(bad_k: object) -> None:
    with pytest.raises(SelectionError):
        select_k([1, 2], bad_k)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "bad_percentile",
    [-1, 101, True, "50", math.nan, math.inf, -math.inf],
)
def test_percentile_rejects_invalid_values(bad_percentile: object) -> None:
    with pytest.raises(SelectionError):
        select_percentile([1, 2], bad_percentile)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_count", [0, -1, True, 1.5])
def test_percentile_to_order_rejects_invalid_item_count(bad_count: object) -> None:
    with pytest.raises(SelectionError):
        percentile_to_order(50, bad_count)  # type: ignore[arg-type]
