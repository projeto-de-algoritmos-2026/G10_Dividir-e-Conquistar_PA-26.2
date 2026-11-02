"""Algoritmos de dividir e conquistar usados pelo RankLab."""

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
from ranklab.algorithms.kendall_tau import (
    KendallTauB,
    KendallTauError,
    compare_rankings_tau_b,
    compare_rankings_with_ties,
)
from ranklab.algorithms.ranking_aggregation import (
    MedianPosition,
    MultiRankingAggregation,
    RankingAggregationError,
    aggregate_rankings,
    aggregate_rankings_by_median,
)
from ranklab.algorithms.ranking_comparison import (
    PAIR_EXPLANATION_ITEM_LIMIT,
    DiscordantPair,
    RankingComparison,
    RankingComparisonError,
    compare_rankings,
    trace_ranking_comparison,
)
from ranklab.algorithms.tracing import (
    TRACE_ITEM_LIMIT,
    AlgorithmTrace,
    TracedResult,
    TraceStep,
)
from ranklab.algorithms.weight_sensitivity import (
    ItemWeightChange,
    WeightScenarioComparison,
    compare_weight_scenarios,
)
from ranklab.algorithms.weight_turning_points import (
    WeightInterval,
    WeightTurningPointAnalysis,
    WeightTurningPointError,
    analyze_weight_turning_points,
    find_weight_turning_points,
)
from ranklab.algorithms.weighted_ranking import (
    AggregatedItem,
    AggregatedRanking,
    CriterionWeight,
    WeightedRankingError,
    aggregate_ranking,
)

__all__ = [
    "PAIR_EXPLANATION_ITEM_LIMIT",
    "TRACE_ITEM_LIMIT",
    "AggregatedItem",
    "AggregatedRanking",
    "AlgorithmTrace",
    "ClosestPair",
    "ClosestPairError",
    "CriterionWeight",
    "DiscordantPair",
    "ItemWeightChange",
    "KendallTauB",
    "KendallTauError",
    "MedianPosition",
    "MultiRankingAggregation",
    "RankingAggregationError",
    "RankingComparison",
    "RankingComparisonError",
    "SelectionError",
    "SelectionResult",
    "TraceStep",
    "TracedResult",
    "WeightInterval",
    "WeightScenarioComparison",
    "WeightTurningPointAnalysis",
    "WeightTurningPointError",
    "WeightedRankingError",
    "aggregate_ranking",
    "aggregate_rankings",
    "aggregate_rankings_by_median",
    "analyze_weight_turning_points",
    "closest_pair",
    "compare_rankings",
    "compare_rankings_tau_b",
    "compare_rankings_with_ties",
    "compare_weight_scenarios",
    "find_weight_turning_points",
    "percentile_to_order",
    "select_k",
    "select_percentile",
    "trace_closest_pair",
    "trace_ranking_comparison",
    "trace_select_k",
    "trace_select_percentile",
]
