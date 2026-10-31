"""Comparação de rankings agregados sob duas configurações de pesos."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ranklab.algorithms.ranking_comparison import (
    RankingComparison,
    compare_rankings,
)
from ranklab.algorithms.weighted_ranking import (
    AggregatedRanking,
    aggregate_ranking,
)
from ranklab.domain.models import Ranking, RankingItem, ScoringMatrix


@dataclass(frozen=True)
class ItemWeightChange:
    """Efeito da alteração de pesos sobre um item.

    ``position_delta`` é positivo quando o item sobe no ranking e negativo
    quando ele cai. ``score_delta`` é calculado como alterado menos base.
    ``crossed_item_ids`` contém os itens cuja ordem relativa foi invertida ou
    ``None`` quando os pares explicativos foram omitidos por tamanho.
    """

    item_id: str
    base_position: int
    changed_position: int
    position_delta: int
    base_score: float
    changed_score: float
    score_delta: float
    crossed_item_ids: tuple[str, ...] | None


@dataclass(frozen=True)
class WeightScenarioComparison:
    """Resultado auditável da comparação entre os dois cenários de pesos."""

    matrix_id: str
    base_ranking: AggregatedRanking
    changed_ranking: AggregatedRanking
    items: tuple[ItemWeightChange, ...]
    ranking_comparison: RankingComparison


def _as_strict_ranking(
    ranking: AggregatedRanking,
    scenario: str,
) -> Ranking:
    """Adapta um ranking agregado ao contrato do comparador por inversões."""

    return Ranking(
        ranking_id=f"{ranking.matrix_id}:{scenario}",
        name=f"Cenário {scenario}",
        origin="ranking agregado por pesos",
        items=tuple(
            RankingItem(item_id=item.item_id, position=item.position)
            for item in ranking.items
        ),
    )


def compare_weight_scenarios(
    matrix: ScoringMatrix,
    base_weights: Mapping[str, float],
    changed_weights: Mapping[str, float],
) -> WeightScenarioComparison:
    """Recalcula e compara o ranking para pesos base e alterados.

    A função delega toda validação, normalização, orientação de critérios e
    desempate a :func:`aggregate_ranking`. A divergência de ordem é delegada a
    :func:`compare_rankings`, preservando a contagem de inversões já adotada
    pelo RankLab.
    """

    base_ranking = aggregate_ranking(matrix, base_weights)
    changed_ranking = aggregate_ranking(matrix, changed_weights)
    ranking_comparison = compare_rankings(
        _as_strict_ranking(base_ranking, "base"),
        _as_strict_ranking(changed_ranking, "alterado"),
    )

    base_positions = {
        item.item_id: item.position
        for item in base_ranking.items
    }
    changed_by_id = {
        item.item_id: item
        for item in changed_ranking.items
    }

    crossed_by_item: dict[str, set[str]] | None
    if ranking_comparison.discordant_pairs is None:
        crossed_by_item = None
    else:
        crossed_by_item = {
            item.item_id: set()
            for item in base_ranking.items
        }
        for pair in ranking_comparison.discordant_pairs:
            crossed_by_item[pair.earlier_in_first].add(pair.later_in_first)
            crossed_by_item[pair.later_in_first].add(pair.earlier_in_first)

    item_changes: list[ItemWeightChange] = []
    for base_item in base_ranking.items:
        changed_item = changed_by_id[base_item.item_id]
        crossed_item_ids = (
            None
            if crossed_by_item is None
            else tuple(
                sorted(
                    crossed_by_item[base_item.item_id],
                    key=base_positions.__getitem__,
                )
            )
        )
        item_changes.append(
            ItemWeightChange(
                item_id=base_item.item_id,
                base_position=base_item.position,
                changed_position=changed_item.position,
                position_delta=base_item.position - changed_item.position,
                base_score=base_item.score,
                changed_score=changed_item.score,
                score_delta=changed_item.score - base_item.score,
                crossed_item_ids=crossed_item_ids,
            )
        )

    return WeightScenarioComparison(
        matrix_id=matrix.matrix_id,
        base_ranking=base_ranking,
        changed_ranking=changed_ranking,
        items=tuple(item_changes),
        ranking_comparison=ranking_comparison,
    )
