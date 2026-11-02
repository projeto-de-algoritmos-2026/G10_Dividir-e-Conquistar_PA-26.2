"""Agregação de vários rankings por distância e posição mediana."""

from __future__ import annotations

from dataclasses import dataclass

from ranklab.algorithms.deterministic_selection import select_k
from ranklab.algorithms.ranking_comparison import compare_rankings
from ranklab.domain.models import Ranking


class RankingAggregationError(ValueError):
    """Entrada incompatível para a agregação de rankings."""


@dataclass(frozen=True)
class MedianPosition:
    item_id: str
    position: float
    positions: tuple[int, ...]


@dataclass(frozen=True)
class MultiRankingAggregation:
    rankings: tuple[Ranking, ...]
    distance_matrix: tuple[tuple[int, ...], ...]
    median_positions: tuple[MedianPosition, ...]


def _validate(rankings: tuple[Ranking, ...]) -> set[str]:
    if len(rankings) < 1:
        raise RankingAggregationError("é necessário informar ao menos um ranking")
    sets = []
    for ranking in rankings:
        if not isinstance(ranking, Ranking) or not ranking.items:
            raise RankingAggregationError("todos os rankings devem ser válidos e não vazios")
        sets.append({item.item_id for item in ranking.items})
    if any(item_set != sets[0] for item_set in sets[1:]):
        raise RankingAggregationError("todos os rankings devem conter exatamente os mesmos item_ids")
    return sets[0]


def aggregate_rankings(rankings: list[Ranking] | tuple[Ranking, ...]) -> MultiRankingAggregation:
    """Calcula distâncias de Kendall e a mediana de posição de cada item.

    Para número par de rankings usa a mediana inferior (ordem ``ceil(n/2)``),
    mantendo a seleção determinística e evitando ordenar a lista completa.
    Empates na posição agregada são desempატados por ``item_id``.
    """
    rankings = tuple(rankings)
    item_ids = _validate(rankings)
    matrix = tuple(
        tuple(compare_rankings(a, b).discordant_pair_count for b in rankings)
        for a in rankings
    )
    by_id: list[MedianPosition] = []
    order = (len(rankings) + 1) // 2
    for item_id in sorted(item_ids):
        positions = tuple(
            next(item.position for item in ranking.items if item.item_id == item_id)
            for ranking in rankings
        )
        selected = select_k(positions, order).value
        by_id.append(MedianPosition(item_id, float(selected), positions))
    by_id.sort(key=lambda result: (result.position, result.item_id))
    return MultiRankingAggregation(rankings, matrix, tuple(by_id))


aggregate_rankings_by_median = aggregate_rankings
