"""Equivalência e invariantes dos rastreamentos didáticos."""

from __future__ import annotations

from ranklab.algorithms import (
    TRACE_ITEM_LIMIT,
    closest_pair,
    compare_rankings,
    select_k,
    trace_closest_pair,
    trace_ranking_comparison,
    trace_select_k,
)
from ranklab.domain.models import (
    Criterion,
    Direction,
    MatrixItem,
    Ranking,
    RankingItem,
    ScoringMatrix,
)


def _ranking(name: str, ids: list[str]) -> Ranking:
    return Ranking(
        name,
        name,
        "teste",
        tuple(RankingItem(item_id, position) for position, item_id in enumerate(ids, 1)),
    )


def _matrix(size: int = 8) -> ScoringMatrix:
    return ScoringMatrix(
        "matrix",
        "Matriz",
        "teste",
        (
            Criterion("x", "X", Direction.HIGHER_IS_BETTER, "u"),
            Criterion("y", "Y", Direction.HIGHER_IS_BETTER, "u"),
        ),
        tuple(
            MatrixItem(f"item-{index:03d}", {"x": float(index), "y": float(index % 3)})
            for index in range(size)
        ),
    )


def test_merge_trace_matches_result_and_sums_inversions() -> None:
    first = _ranking("first", ["a", "b", "c", "d"])
    second = _ranking("second", ["d", "c", "b", "a"])

    traced = trace_ranking_comparison(first, second)

    assert traced.result == compare_rankings(first, second)
    assert traced.trace.steps is not None
    assert sum(
        step.state["inversions_added"]
        for step in traced.trace.steps
        if step.kind == "merge"
    ) == traced.result.discordant_pair_count


def test_selection_trace_matches_result_and_keeps_duplicates_in_partitions() -> None:
    values = [9, 2, 7, 2, 5, 2, 8, 1, 6, 4, 3]

    traced = trace_select_k(values, 4)

    assert traced.result == select_k(values, 4)
    assert traced.trace.steps is not None
    partition_values = [
        value
        for step in traced.trace.steps
        if step.kind == "partition"
        for key in ("lower", "equal", "higher")
        for value in step.state[key]
    ]
    assert partition_values.count(2) >= 3


def test_closest_pair_trace_matches_result_and_exposes_strip() -> None:
    matrix = _matrix()

    traced = trace_closest_pair(matrix, ("x", "y"))

    assert traced.result == closest_pair(matrix, ("x", "y"))
    assert traced.trace.steps is not None
    combines = [step for step in traced.trace.steps if step.kind == "combine"]
    assert combines
    assert all("delta" in step.state and "strip" in step.state for step in combines)


def test_every_materialized_step_has_text() -> None:
    traced = trace_select_k(list(range(12, 0, -1)), 6)

    assert traced.trace.steps
    assert all(step.description.strip() for step in traced.trace.steps)


def test_trace_is_omitted_above_shared_limit_without_changing_result() -> None:
    values = list(range(TRACE_ITEM_LIMIT + 1, 0, -1))

    traced = trace_select_k(values, 10)

    assert traced.result == select_k(values, 10)
    assert traced.trace.status == "omitted"
    assert traced.trace.steps is None
    assert traced.trace.limit == TRACE_ITEM_LIMIT
