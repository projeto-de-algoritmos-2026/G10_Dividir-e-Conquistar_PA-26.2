"""Pontos exatos de virada entre dois cenários de pesos."""

from __future__ import annotations

import itertools
from collections.abc import Mapping
from dataclasses import dataclass

from ranklab.algorithms.weighted_ranking import (
    AggregatedRanking,
    aggregate_ranking,
)
from ranklab.domain.models import ScoringMatrix


class WeightTurningPointError(ValueError):
    pass


@dataclass(frozen=True)
class WeightInterval:
    start: float
    end: float
    item_ids: tuple[str, ...]


@dataclass(frozen=True)
class WeightTurningPointAnalysis:
    base: AggregatedRanking
    changed: AggregatedRanking
    turning_points: tuple[float, ...]
    intervals: tuple[WeightInterval, ...]


def analyze_weight_turning_points(
    matrix: ScoringMatrix,
    base_weights: Mapping[str, float],
    changed_weights: Mapping[str, float],
) -> WeightTurningPointAnalysis:
    base = aggregate_ranking(matrix, base_weights)
    changed = aggregate_ranking(matrix, changed_weights)
    base_scores = {item.item_id: item.score for item in base.items}
    changed_scores = {item.item_id: item.score for item in changed.items}
    points = {0.0, 1.0}
    ids = sorted(base_scores)
    for left_index, left in enumerate(ids):
        for right in ids[left_index + 1:]:
            delta0 = base_scores[left] - base_scores[right]
            delta1 = changed_scores[left] - changed_scores[right]
            slope = delta1 - delta0
            if slope == 0:
                continue
            t = -delta0 / slope
            if 0.0 < t < 1.0:
                points.add(t)
    sorted_points = tuple(sorted(points))
    intervals = []
    for start, end in itertools.pairwise(sorted_points):
        sample = (start + end) / 2
        scores = {
            item_id: base_scores[item_id] + sample * (changed_scores[item_id] - base_scores[item_id])
            for item_id in ids
        }
        order = tuple(sorted(ids, key=lambda item_id: (-scores[item_id], item_id)))
        intervals.append(WeightInterval(start, end, order))
    return WeightTurningPointAnalysis(base, changed, sorted_points, tuple(intervals))


find_weight_turning_points = analyze_weight_turning_points
