from __future__ import annotations

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


@pytest.mark.parametrize("operation", ["empty", "bad_k", "bad_percentile"])
def test_selection_rejects_invalid_contract(operation: str) -> None:
    with pytest.raises(SelectionError):
        if operation == "empty":
            select_k([], 1)
        elif operation == "bad_k":
            select_k([1, 2], 0)
        else:
            select_percentile([1, 2], 101)
