"""Construção de relatórios reproduzíveis para as análises do RankLab."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ranklab.algorithms import (
    AggregatedRanking,
    ClosestPair,
    RankingComparison,
    SelectionResult,
    WeightScenarioComparison,
)
from ranklab.domain.models import Ranking, ScoringMatrix


def _ranking_comparison_section(
    first: Ranking,
    second: Ranking,
    comparison: RankingComparison,
) -> dict[str, Any]:
    second_positions = {item.item_id: item.position for item in second.items}
    positions = [
        {
            "item_id": item.item_id,
            "first_position": item.position,
            "second_position": second_positions[item.item_id],
            "position_delta": item.position - second_positions[item.item_id],
        }
        for item in first.items
    ]
    pairs = (
        [
            {
                "earlier_in_first": pair.earlier_in_first,
                "later_in_first": pair.later_in_first,
            }
            for pair in comparison.discordant_pairs
        ]
        if comparison.discordant_pairs is not None
        else None
    )
    return {
        "question": "Quantos pares inverteram de ordem entre dois rankings?",
        "first": {
            "ranking_id": first.ranking_id,
            "name": first.name,
            "origin": first.origin,
        },
        "second": {
            "ranking_id": second.ranking_id,
            "name": second.name,
            "origin": second.origin,
        },
        "positions": positions,
        "discordant_pair_count": comparison.discordant_pair_count,
        "possible_pair_count": comparison.possible_pair_count,
        "kendall_normalized_distance": comparison.normalized_distance,
        "discordant_pairs": pairs,
        "pair_explanation": (
            "Pares omitidos porque o limite de explicação foi excedido."
            if pairs is None
            else "Cada par listado aparece em ordem oposta nos dois rankings."
        ),
    }


def _aggregated_ranking(ranking: AggregatedRanking) -> dict[str, Any]:
    return {
        "matrix_id": ranking.matrix_id,
        "weights": [
            {
                "criterion_id": weight.criterion_id,
                "input": weight.input_weight,
                "normalized": weight.normalized_weight,
            }
            for weight in ranking.weights
        ],
        "items": [
            {
                "item_id": item.item_id,
                "position": item.position,
                "normalized_values": dict(sorted(item.normalized_values.items())),
                "score": item.score,
            }
            for item in ranking.items
        ],
        "normalization": ranking.normalization,
        "aggregation": ranking.aggregation,
        "tie_break": ranking.tie_break,
    }


def _sensitivity_section(result: WeightScenarioComparison) -> dict[str, Any]:
    return {
        "question": "Quais itens e posições mudaram após alterar os pesos?",
        "base": _aggregated_ranking(result.base_ranking),
        "changed": _aggregated_ranking(result.changed_ranking),
        "items": [
            {
                "item_id": item.item_id,
                "base_position": item.base_position,
                "changed_position": item.changed_position,
                "position_delta": item.position_delta,
                "base_score": item.base_score,
                "changed_score": item.changed_score,
                "score_delta": item.score_delta,
                "crossed_item_ids": item.crossed_item_ids,
            }
            for item in result.items
        ],
        "ranking_divergence": {
            "discordant_pair_count": result.ranking_comparison.discordant_pair_count,
            "possible_pair_count": result.ranking_comparison.possible_pair_count,
            "kendall_normalized_distance": (
                result.ranking_comparison.normalized_distance
            ),
        },
    }


def build_audit_report(
    *,
    matrix: ScoringMatrix,
    matrix_path: Path,
    first_ranking: Ranking,
    first_ranking_path: Path,
    second_ranking: Ranking,
    second_ranking_path: Path,
    ranking_comparison: RankingComparison,
    closest: ClosestPair,
    closest_criteria: tuple[str, str],
    selection: SelectionResult,
    selection_path: Path,
    sensitivity: WeightScenarioComparison,
    base_weights_path: Path,
    changed_weights_path: Path,
) -> dict[str, Any]:
    criteria = {criterion.criterion_id: criterion for criterion in matrix.criteria}
    closest_items = {
        item.item_id: item
        for item in matrix.items
        if item.item_id in {closest.first_item_id, closest.second_item_id}
    }
    return {
        "format": "ranklab-audit-report",
        "format_version": 1,
        "inputs": {
            "matrix": str(matrix_path),
            "first_ranking": str(first_ranking_path),
            "second_ranking": str(second_ranking_path),
            "selection_values": str(selection_path),
            "base_weights": str(base_weights_path),
            "changed_weights": str(changed_weights_path),
        },
        "matrix": {
            "matrix_id": matrix.matrix_id,
            "name": matrix.name,
            "origin": matrix.origin,
            "criteria": [
                {
                    "criterion_id": criterion.criterion_id,
                    "name": criterion.name,
                    "direction": criterion.direction.value,
                    "unit": criterion.unit,
                }
                for criterion in matrix.criteria
            ],
        },
        "analyses": {
            "ordering_divergence": _ranking_comparison_section(
                first_ranking, second_ranking, ranking_comparison
            ),
            "proximity": {
                "question": "Quais dois perfis são próximos nos atributos escolhidos?",
                "item_ids": [closest.first_item_id, closest.second_item_id],
                "criterion_ids": list(closest_criteria),
                "criterion_definitions": [
                    {
                        "criterion_id": criterion_id,
                        "name": criteria[criterion_id].name,
                        "direction": criteria[criterion_id].direction.value,
                        "unit": criteria[criterion_id].unit,
                    }
                    for criterion_id in closest_criteria
                ],
                "source_values": {
                    item_id: {
                        criterion_id: closest_items[item_id].values[criterion_id]
                        for criterion_id in closest_criteria
                    }
                    for item_id in (closest.first_item_id, closest.second_item_id)
                },
                "distance": closest.distance,
                "normalization": closest.normalization,
                "metric": closest.metric,
                "interpretation": (
                    "Proximidade somente nos dois atributos escolhidos; "
                    "não representa similaridade geral."
                ),
                "limitations": [
                    "O MVP aceita exatamente dois atributos quantitativos.",
                    "A distância depende da normalização e da métrica declaradas.",
                ],
            },
            "median_position": {
                "question": "Qual elemento ocupa a ordem solicitada na coleção?",
                "input": str(selection_path),
                "order": selection.order,
                "percentile": selection.percentile,
                "value": selection.value,
                "definition": (
                    "Seleção de ordem; não é posição em um ranking agregado."
                ),
            },
            "weight_sensitivity": _sensitivity_section(sensitivity),
        },
    }


def write_audit_report(report: dict[str, Any], output: Path | None) -> str:
    """Serializa um relatório de forma determinística e opcionalmente grava-o."""

    import json

    serialized = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if output is not None:
        try:
            output.write_text(serialized, encoding="utf-8")
        except OSError as exc:
            raise OSError(f"{output}: não foi possível escrever o relatório: {exc}") from exc
    return serialized
