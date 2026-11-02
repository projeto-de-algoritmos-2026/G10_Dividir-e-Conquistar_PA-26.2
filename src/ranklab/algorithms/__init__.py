"""Algoritmos de dividir e conquistar usados pelo RankLab."""

from ranklab.algorithms.ranking_comparison import (
    PAIR_EXPLANATION_ITEM_LIMIT,
    DiscordantPair,
    RankingComparison,
    RankingComparisonError,
    compare_rankings,
    trace_ranking_comparison,
)
from ranklab.algorithms.closest_pair import (
    ClosestPair,
    ClosestPairError,
    closest_pair,
    trace_closest_pair,
)
from ranklab.algorithms.deterministic_selection import (
    SelectionError,
    SelectionResult,
    percentile_to_order,
    select_k,
    select_percentile,
    trace_select_k,
    trace_select_percentile,
)
from ranklab.algorithms.tracing import (
    TRACE_ITEM_LIMIT,
    AlgorithmTrace,
    TraceStep,
    TracedResult,
)
from ranklab.algorithms.weighted_ranking import (
    AggregatedItem,
    AggregatedRanking,
    CriterionWeight,
    WeightedRankingError,
    aggregate_ranking,
)
from ranklab.algorithms.weight_sensitivity import (
    ItemWeightChange,
    WeightScenarioComparison,
    compare_weight_scenarios,
)

__all__ = [
    "PAIR_EXPLANATION_ITEM_LIMIT",
    "DiscordantPair",
    "RankingComparison",
    "RankingComparisonError",
    "compare_rankings",
    "trace_ranking_comparison",
    "ClosestPair",
    "ClosestPairError",
    "closest_pair",
    "trace_closest_pair",
    "SelectionError",
    "SelectionResult",
    "percentile_to_order",
    "select_k",
    "select_percentile",
    "trace_select_k",
    "trace_select_percentile",
    "TRACE_ITEM_LIMIT",
    "AlgorithmTrace",
    "TraceStep",
    "TracedResult",
    "AggregatedItem",
    "AggregatedRanking",
    "CriterionWeight",
    "WeightedRankingError",
    "aggregate_ranking",
    "ItemWeightChange",
    "WeightScenarioComparison",
    "compare_weight_scenarios",
]
