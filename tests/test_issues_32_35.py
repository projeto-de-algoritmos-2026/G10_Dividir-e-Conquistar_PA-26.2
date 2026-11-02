from ranklab.algorithms import (
    aggregate_rankings,
    analyze_weight_turning_points,
    compare_rankings_tau_b,
)
from ranklab.domain.models import (
    Criterion,
    Direction,
    MatrixItem,
    Ranking,
    RankingItem,
    ScoringMatrix,
)


def _ranking(name, order):
    return Ranking(name, name, "test", tuple(RankingItem(item, position) for position, item in enumerate(order, 1)))


def test_aggregate_rankings_has_symmetric_distances_and_median():
    result = aggregate_rankings([_ranking("a", ["a", "b"]), _ranking("b", ["b", "a"]), _ranking("c", ["a", "b"])])
    assert result.distance_matrix == ((0, 1, 0), (1, 0, 1), (0, 1, 0))
    assert [(item.item_id, item.position) for item in result.median_positions] == [("a", 1.0), ("b", 2.0)]


def test_turning_point_is_exact():
    matrix = ScoringMatrix("m", "m", "test", (
        Criterion("x", "X", Direction.HIGHER_IS_BETTER, "u"),
        Criterion("y", "Y", Direction.HIGHER_IS_BETTER, "u"),
    ), (MatrixItem("a", {"x": 1, "y": 0}), MatrixItem("b", {"x": 0, "y": 1})))
    result = analyze_weight_turning_points(matrix, {"x": 1, "y": 0}, {"x": 0, "y": 1})
    assert result.turning_points == (0.0, 0.5, 1.0)


def test_tau_b_supports_ties():
    first = _ranking("first", ["a", "b", "c"])
    first = Ranking(
        first.ranking_id,
        first.name,
        first.origin,
        (RankingItem("a", 1), RankingItem("b", 1), RankingItem("c", 3)),
    )
    second = Ranking(
        "second",
        "second",
        "test",
        (RankingItem("a", 1), RankingItem("b", 2), RankingItem("c", 2)),
    )
    assert compare_rankings_tau_b(first, second).tau_b == 0.5
