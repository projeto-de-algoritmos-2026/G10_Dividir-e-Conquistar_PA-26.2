"""Testes da comparação de cenários de pesos."""

from __future__ import annotations

import pytest

from ranklab.algorithms import (
    PAIR_EXPLANATION_ITEM_LIMIT,
    WeightedRankingError,
    compare_weight_scenarios,
)
from ranklab.domain.models import (
    Criterion,
    Direction,
    MatrixItem,
    ScoringMatrix,
)


def _matrix(
    rows: list[tuple[str, float, float]],
) -> ScoringMatrix:
    return ScoringMatrix(
        matrix_id="fornecedores",
        name="Fornecedores",
        origin="teste",
        criteria=(
            Criterion(
                "qualidade",
                "Qualidade",
                Direction.HIGHER_IS_BETTER,
                "pontos",
            ),
            Criterion(
                "prazo_dias",
                "Prazo",
                Direction.LOWER_IS_BETTER,
                "dias",
            ),
        ),
        items=tuple(
            MatrixItem(
                item_id,
                {"qualidade": qualidade, "prazo_dias": prazo},
            )
            for item_id, qualidade, prazo in rows
        ),
    )


def _example_matrix() -> ScoringMatrix:
    return _matrix(
        [
            ("fornecedor-a", 92.5, 12),
            ("fornecedor-b", 88, 9),
            ("fornecedor-c", 90, 15),
        ]
    )


def test_weight_change_reorders_and_explains_items() -> None:
    result = compare_weight_scenarios(
        _example_matrix(),
        {"qualidade": 2, "prazo_dias": 1},
        {"qualidade": 1, "prazo_dias": 3},
    )

    assert [item.item_id for item in result.base_ranking.items] == [
        "fornecedor-a",
        "fornecedor-b",
        "fornecedor-c",
    ]
    assert [item.item_id for item in result.changed_ranking.items] == [
        "fornecedor-b",
        "fornecedor-a",
        "fornecedor-c",
    ]
    assert result.ranking_comparison.discordant_pair_count == 1
    assert result.ranking_comparison.possible_pair_count == 3
    assert result.ranking_comparison.normalized_distance == pytest.approx(1 / 3)

    by_id = {item.item_id: item for item in result.items}
    assert by_id["fornecedor-a"].position_delta == -1
    assert by_id["fornecedor-a"].crossed_item_ids == ("fornecedor-b",)
    assert by_id["fornecedor-b"].position_delta == 1
    assert by_id["fornecedor-b"].crossed_item_ids == ("fornecedor-a",)
    assert by_id["fornecedor-c"].position_delta == 0
    assert by_id["fornecedor-c"].crossed_item_ids == ()
    assert by_id["fornecedor-a"].score_delta == pytest.approx(0.625 - 5 / 6)
    assert by_id["fornecedor-b"].score_delta == pytest.approx(0.75 - 1 / 3)


def test_weight_change_can_change_scores_without_changing_order() -> None:
    result = compare_weight_scenarios(
        _example_matrix(),
        {"qualidade": 2, "prazo_dias": 1},
        {"qualidade": 3, "prazo_dias": 2},
    )

    assert [item.item_id for item in result.base_ranking.items] == [
        "fornecedor-a",
        "fornecedor-b",
        "fornecedor-c",
    ]
    assert [item.item_id for item in result.changed_ranking.items] == [
        "fornecedor-a",
        "fornecedor-b",
        "fornecedor-c",
    ]
    assert result.ranking_comparison.discordant_pair_count == 0
    assert all(item.position_delta == 0 for item in result.items)
    assert all(item.crossed_item_ids == () for item in result.items)
    assert any(item.score_delta != 0 for item in result.items)


def test_both_scenarios_report_weights_and_preserve_shared_policies() -> None:
    result = compare_weight_scenarios(
        _example_matrix(),
        {"qualidade": 2, "prazo_dias": 1},
        {"qualidade": 1, "prazo_dias": 3},
    )

    assert [weight.input_weight for weight in result.base_ranking.weights] == [
        2.0,
        1.0,
    ]
    assert [weight.normalized_weight for weight in result.base_ranking.weights] == pytest.approx(
        [2 / 3, 1 / 3]
    )
    assert [weight.input_weight for weight in result.changed_ranking.weights] == [
        1.0,
        3.0,
    ]
    assert [weight.normalized_weight for weight in result.changed_ranking.weights] == pytest.approx(
        [1 / 4, 3 / 4]
    )
    assert result.base_ranking.normalization == result.changed_ranking.normalization
    assert result.base_ranking.aggregation == result.changed_ranking.aggregation
    assert result.base_ranking.tie_break == result.changed_ranking.tie_break

    base_values = {
        item.item_id: item.normalized_values
        for item in result.base_ranking.items
    }
    changed_values = {
        item.item_id: item.normalized_values
        for item in result.changed_ranking.items
    }
    assert base_values == changed_values


def test_exact_score_tie_keeps_lexicographic_tie_break() -> None:
    result = compare_weight_scenarios(
        _example_matrix(),
        {"qualidade": 2, "prazo_dias": 1},
        {"qualidade": 1, "prazo_dias": 2},
    )

    assert result.changed_ranking.items[0].score == pytest.approx(
        result.changed_ranking.items[1].score
    )
    assert [item.item_id for item in result.changed_ranking.items[:2]] == [
        "fornecedor-a",
        "fornecedor-b",
    ]


@pytest.mark.parametrize(
    ("base_weights", "changed_weights"),
    [
        (
            {"qualidade": -1, "prazo_dias": 1},
            {"qualidade": 1, "prazo_dias": 1},
        ),
        (
            {"qualidade": 1, "prazo_dias": 1},
            {"qualidade": 0, "prazo_dias": 0},
        ),
        (
            {"qualidade": 1, "prazo_dias": 1},
            {"qualidade": 1},
        ),
    ],
)
def test_invalid_weights_in_either_scenario_are_rejected(
    base_weights: dict[str, float],
    changed_weights: dict[str, float],
) -> None:
    with pytest.raises(WeightedRankingError):
        compare_weight_scenarios(
            _example_matrix(),
            base_weights,
            changed_weights,
        )


def test_large_comparison_keeps_changes_but_omits_crossed_item_lists() -> None:
    item_count = PAIR_EXPLANATION_ITEM_LIMIT + 1
    matrix = _matrix(
        [
            (f"item-{index:03d}", float(index), float(index))
            for index in range(item_count)
        ]
    )

    result = compare_weight_scenarios(
        matrix,
        {"qualidade": 1, "prazo_dias": 0},
        {"qualidade": 0, "prazo_dias": 1},
    )

    assert result.ranking_comparison.discordant_pair_count == 5_050
    assert result.ranking_comparison.discordant_pairs is None
    assert all(item.crossed_item_ids is None for item in result.items)
