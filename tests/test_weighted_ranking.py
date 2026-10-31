from __future__ import annotations

import math

import pytest

from ranklab.algorithms import WeightedRankingError, aggregate_ranking
from ranklab.domain.models import Criterion, Direction, MatrixItem, ScoringMatrix


def _matrix(
    items: list[tuple[str, float, float]],
    *,
    reverse_criteria: bool = False,
) -> ScoringMatrix:
    criteria = [
        Criterion("beneficio", "Benefício", Direction.HIGHER_IS_BETTER, "u"),
        Criterion("custo", "Custo", Direction.LOWER_IS_BETTER, "u"),
    ]
    if reverse_criteria:
        criteria.reverse()
    return ScoringMatrix(
        matrix_id="m",
        name="teste",
        origin="teste",
        criteria=tuple(criteria),
        items=tuple(
            MatrixItem(
                item_id=item_id,
                values={"beneficio": beneficio, "custo": custo},
            )
            for item_id, beneficio, custo in items
        ),
    )


def test_manual_example_exposes_normalized_values_weights_scores_and_order() -> None:
    result = aggregate_ranking(
        _matrix([("a", 10, 10), ("b", 20, 20), ("c", 30, 10)]),
        {"beneficio": 3, "custo": 1},
    )

    assert result.matrix_id == "m"
    assert result.normalization == "min-max orientada pela direção"
    assert result.aggregation == "soma ponderada"
    assert [
        (weight.criterion_id, weight.input_weight, weight.normalized_weight)
        for weight in result.weights
    ] == [
        ("beneficio", 3.0, 0.75),
        ("custo", 1.0, 0.25),
    ]
    assert [(item.position, item.item_id) for item in result.items] == [
        (1, "c"),
        (2, "b"),
        (3, "a"),
    ]

    by_id = {item.item_id: item for item in result.items}
    assert by_id["a"].normalized_values == {"beneficio": 0.0, "custo": 1.0}
    assert by_id["b"].normalized_values == {"beneficio": 0.5, "custo": 0.0}
    assert by_id["c"].normalized_values == {"beneficio": 1.0, "custo": 1.0}
    assert by_id["a"].score == pytest.approx(0.25)
    assert by_id["b"].score == pytest.approx(0.375)
    assert by_id["c"].score == pytest.approx(1.0)


def test_constant_column_is_zero_and_does_not_change_order() -> None:
    result = aggregate_ranking(
        _matrix([("b", 10, 5), ("a", 20, 5), ("c", 30, 5)]),
        {"beneficio": 1, "custo": 99},
    )

    assert [item.item_id for item in result.items] == ["c", "a", "b"]
    assert all(item.normalized_values["custo"] == 0.0 for item in result.items)
    assert [item.score for item in result.items] == pytest.approx([0.01, 0.005, 0.0])


def test_accepts_zero_weight_and_normalizes_sum_different_from_one() -> None:
    result = aggregate_ranking(
        _matrix([("a", 0, 100), ("b", 10, 0)]),
        {"beneficio": 0, "custo": 4},
    )

    assert [weight.normalized_weight for weight in result.weights] == [0.0, 1.0]
    assert [(item.item_id, item.score) for item in result.items] == [
        ("b", 1.0),
        ("a", 0.0),
    ]


@pytest.mark.parametrize(
    "weights",
    [
        {"beneficio": -1, "custo": 1},
        {"beneficio": True, "custo": 1},
        {"beneficio": "1", "custo": 1},
        {"beneficio": math.nan, "custo": 1},
        {"beneficio": math.inf, "custo": 1},
        {"beneficio": -math.inf, "custo": 1},
        {"beneficio": 0, "custo": 0},
        {"beneficio": 1},
        {"beneficio": 1, "custo": 1, "extra": 1},
    ],
)
def test_rejects_invalid_weights(weights: dict[str, object]) -> None:
    with pytest.raises(WeightedRankingError):
        aggregate_ranking(
            _matrix([("a", 1, 1), ("b", 2, 2)]),
            weights,  # type: ignore[arg-type]
        )


def test_rejects_non_mapping_weights() -> None:
    with pytest.raises(WeightedRankingError, match="mapping"):
        aggregate_ranking(  # type: ignore[arg-type]
            _matrix([("a", 1, 1), ("b", 2, 2)]),
            [("beneficio", 1), ("custo", 1)],
        )


def test_rejects_integer_weight_too_large_for_float_as_domain_error() -> None:
    with pytest.raises(WeightedRankingError, match="número finito"):
        aggregate_ranking(
            _matrix([("a", 1, 1), ("b", 2, 2)]),
            {"beneficio": 10**400, "custo": 1},
        )


@pytest.mark.parametrize("bad_value", [True, "1", None, math.nan, math.inf])
def test_rejects_invalid_matrix_values_built_outside_reader(bad_value: object) -> None:
    matrix = _matrix([("a", 1, 1), ("b", 2, 2)])
    invalid = ScoringMatrix(
        matrix_id=matrix.matrix_id,
        name=matrix.name,
        origin=matrix.origin,
        criteria=matrix.criteria,
        items=(
            MatrixItem("a", {"beneficio": bad_value, "custo": 1}),  # type: ignore[dict-item]
            matrix.items[1],
        ),
    )

    with pytest.raises(WeightedRankingError, match="número finito"):
        aggregate_ranking(invalid, {"beneficio": 1, "custo": 1})


def test_rejects_missing_matrix_value_built_outside_reader() -> None:
    matrix = _matrix([("a", 1, 1), ("b", 2, 2)])
    invalid = ScoringMatrix(
        matrix_id=matrix.matrix_id,
        name=matrix.name,
        origin=matrix.origin,
        criteria=matrix.criteria,
        items=(MatrixItem("a", {"beneficio": 1}), matrix.items[1]),
    )

    with pytest.raises(WeightedRankingError, match="sem critérios"):
        aggregate_ranking(invalid, {"beneficio": 1, "custo": 1})


def test_rejects_integer_matrix_value_too_large_for_float_as_domain_error() -> None:
    matrix = _matrix([("a", 1, 1), ("b", 2, 2)])
    invalid = ScoringMatrix(
        matrix_id=matrix.matrix_id,
        name=matrix.name,
        origin=matrix.origin,
        criteria=matrix.criteria,
        items=(
            MatrixItem("a", {"beneficio": 10**400, "custo": 1}),
            matrix.items[1],
        ),
    )

    with pytest.raises(WeightedRankingError, match="número finito"):
        aggregate_ranking(invalid, {"beneficio": 1, "custo": 1})


def test_exact_score_tie_uses_item_id_independent_of_input_order() -> None:
    first = aggregate_ranking(
        _matrix([("z", 5, 5), ("a", 5, 5)]),
        {"beneficio": 1, "custo": 1},
    )
    second = aggregate_ranking(
        _matrix([("a", 5, 5), ("z", 5, 5)]),
        {"beneficio": 1, "custo": 1},
    )

    assert [item.item_id for item in first.items] == ["a", "z"]
    assert first.items == second.items


def test_result_is_invariant_to_item_criterion_and_weight_mapping_order() -> None:
    original = aggregate_ranking(
        _matrix([("c", 30, 10), ("a", 10, 10), ("b", 20, 20)]),
        {"beneficio": 3, "custo": 1},
    )
    permuted = aggregate_ranking(
        _matrix(
            [("b", 20, 20), ("c", 30, 10), ("a", 10, 10)],
            reverse_criteria=True,
        ),
        {"custo": 1, "beneficio": 3},
    )

    original_by_id = {
        item.item_id: (item.position, item.score, item.normalized_values)
        for item in original.items
    }
    permuted_by_id = {
        item.item_id: (item.position, item.score, item.normalized_values)
        for item in permuted.items
    }
    assert original_by_id == permuted_by_id


def test_valid_values_and_scores_stay_in_unit_interval() -> None:
    result = aggregate_ranking(
        _matrix([("a", -20, -5), ("b", 0, 100), ("c", 50, 2)]),
        {"beneficio": 2, "custo": 7},
    )

    for item in result.items:
        assert 0.0 <= item.score <= 1.0
        assert all(0.0 <= value <= 1.0 for value in item.normalized_values.values())


def test_handles_finite_values_and_weights_without_intermediate_overflow() -> None:
    result = aggregate_ranking(
        _matrix([("a", -1e308, 1e308), ("b", 1e308, -1e308)]),
        {"beneficio": 1e308, "custo": 1e308},
    )

    assert [weight.normalized_weight for weight in result.weights] == [0.5, 0.5]
    assert [(item.item_id, item.score) for item in result.items] == [
        ("b", 1.0),
        ("a", 0.0),
    ]


@pytest.mark.parametrize(
    "matrix",
    [
        "not-a-matrix",
        ScoringMatrix("m", "n", "o", (), (MatrixItem("a", {}),)),
        ScoringMatrix(
            "m",
            "n",
            "o",
            (Criterion("x", "X", Direction.HIGHER_IS_BETTER, "u"),),
            (),
        ),
    ],
)
def test_rejects_invalid_or_empty_matrix(matrix: object) -> None:
    with pytest.raises(WeightedRankingError):
        aggregate_ranking(matrix, {"x": 1})  # type: ignore[arg-type]
