from __future__ import annotations

import itertools
import math
import random

import pytest

from ranklab.algorithms import ClosestPairError, closest_pair
from ranklab.domain.models import Criterion, Direction, MatrixItem, ScoringMatrix


def _matrix(items: list[tuple[str, float, float]]) -> ScoringMatrix:
    return ScoringMatrix(
        matrix_id="m",
        name="teste",
        origin="teste",
        criteria=(
            Criterion("x", "Eixo X", Direction.HIGHER_IS_BETTER, "u"),
            Criterion("y", "Eixo Y", Direction.LOWER_IS_BETTER, "u"),
        ),
        items=tuple(
            MatrixItem(item_id=item_id, values={"x": x, "y": y})
            for item_id, x, y in items
        ),
    )


def _quadratic_closest_pair(
    matrix: ScoringMatrix,
    criterion_ids: tuple[str, str],
) -> tuple[tuple[str, str], float]:
    """Oráculo independente com normalização e enumeração de todos os pares."""

    criteria = {criterion.criterion_id: criterion for criterion in matrix.criteria}
    normalized_columns: dict[str, dict[str, float]] = {}
    for criterion_id in criterion_ids:
        values = [item.values[criterion_id] for item in matrix.items]
        minimum = min(values)
        maximum = max(values)
        normalized_columns[criterion_id] = {}
        for item in matrix.items:
            if maximum == minimum:
                normalized = 0.0
            else:
                normalized = (item.values[criterion_id] - minimum) / (
                    maximum - minimum
                )
                if criteria[criterion_id].direction is Direction.LOWER_IS_BETTER:
                    normalized = 1.0 - normalized
            normalized_columns[criterion_id][item.item_id] = normalized

    candidates: list[tuple[float, tuple[str, str]]] = []
    for first, second in itertools.combinations(matrix.items, 2):
        distance = math.hypot(
            normalized_columns[criterion_ids[0]][first.item_id]
            - normalized_columns[criterion_ids[0]][second.item_id],
            normalized_columns[criterion_ids[1]][first.item_id]
            - normalized_columns[criterion_ids[1]][second.item_id],
        )
        candidates.append((distance, tuple(sorted((first.item_id, second.item_id)))))

    best_distance, best_pair = candidates[0]
    for distance, pair in candidates[1:]:
        if distance < best_distance and not math.isclose(
            distance, best_distance, rel_tol=1e-12, abs_tol=1e-15
        ):
            best_distance, best_pair = distance, pair
        elif math.isclose(
            distance, best_distance, rel_tol=1e-12, abs_tol=1e-15
        ) and pair < best_pair:
            best_distance, best_pair = distance, pair
    return best_pair, best_distance


def test_closest_pair_normalizes_scales_and_respects_direction() -> None:
    result = closest_pair(
        _matrix([("a", 0, 1000), ("b", 10, 990), ("c", 100, 0)]),
        ("x", "y"),
    )

    assert (result.first_item_id, result.second_item_id) == ("a", "b")
    assert result.distance == pytest.approx((0.1**2 + 0.01**2) ** 0.5)
    assert result.criterion_ids == ("x", "y")


def test_two_items_are_always_the_closest_pair() -> None:
    result = closest_pair(_matrix([("b", -10, 50), ("a", 30, -20)]), ("x", "y"))

    assert (result.first_item_id, result.second_item_id) == ("a", "b")
    assert result.distance == pytest.approx(math.sqrt(2))


def test_closest_pair_uses_lexicographic_tie_break() -> None:
    result = closest_pair(
        _matrix([("z", 0, 0), ("b", 1, 1), ("a", 2, 2), ("c", 3, 3)]),
        ("x", "y"),
    )

    assert (result.first_item_id, result.second_item_id) == ("a", "b")


def test_tie_break_precedes_floating_point_rounding_noise() -> None:
    result = closest_pair(
        _matrix(
            [
                ("id-01", 3, 4),
                ("id-00", 4, 4),
                ("id-02", 1, 1),
                ("id-03", 1, 2),
            ]
        ),
        ("x", "y"),
    )

    assert (result.first_item_id, result.second_item_id) == ("id-00", "id-01")


def test_strip_includes_boundary_despite_floating_point_rounding_noise() -> None:
    result = closest_pair(
        _matrix(
            [
                ("id-03", 3, 0),
                ("id-00", 0, 3),
                ("id-01", 1, 0),
                ("id-02", 3, 2),
            ]
        ),
        ("x", "y"),
    )

    assert (result.first_item_id, result.second_item_id) == ("id-01", "id-03")


def test_constant_dimension_is_projected_to_zero() -> None:
    result = closest_pair(
        _matrix([("a", 0, 5), ("b", 10, 5), ("c", 20, 5)]),
        ("x", "y"),
    )

    assert result.distance == pytest.approx(0.5)
    assert (result.first_item_id, result.second_item_id) == ("a", "b")


def test_two_constant_dimensions_and_coincident_points_use_lexicographic_pair() -> None:
    items = [(item_id, -5, -5) for item_id in reversed("abcdefghij")]

    result = closest_pair(_matrix(items), ("x", "y"))

    assert result.distance == 0.0
    assert (result.first_item_id, result.second_item_id) == ("a", "b")


def test_closest_pair_crossing_recursive_split_is_found() -> None:
    matrix = _matrix(
        [
            ("far-left", -100, 100),
            ("left", -0.01, 0.01),
            ("right", 0.01, -0.01),
            ("far-right", 100, -100),
        ]
    )

    result = closest_pair(matrix, ("x", "y"))

    assert (result.first_item_id, result.second_item_id) == ("left", "right")


@pytest.mark.parametrize(
    "items",
    [
        [("a", -10, 3), ("b", -9, 3), ("c", 20, 3)],
        [("a", -4, -4), ("b", 0, 0), ("c", 4, 4), ("d", 9, 9)],
        [("z", 0, 0), ("b", 1, 1), ("a", 2, 2), ("c", 3, 3)],
    ],
)
def test_adversarial_inputs_match_quadratic_oracle(
    items: list[tuple[str, float, float]],
) -> None:
    matrix = _matrix(items)
    expected_pair, expected_distance = _quadratic_closest_pair(matrix, ("x", "y"))

    result = closest_pair(matrix, ("x", "y"))

    assert (result.first_item_id, result.second_item_id) == expected_pair
    assert result.distance == pytest.approx(expected_distance)


def test_deterministic_small_point_sets_match_quadratic_oracle() -> None:
    generator = random.Random(2026)

    for size in (2, 3, 4, 7, 16, 32):
        for case in range(8):
            items = [
                (
                    f"item-{index:02d}",
                    generator.uniform(-1000, 1000) + index * 1e-6,
                    generator.uniform(-1000, 1000) - index * 1e-6,
                )
                for index in range(size)
            ]
            matrix = _matrix(items)
            expected_pair, expected_distance = _quadratic_closest_pair(
                matrix, ("x", "y")
            )

            result = closest_pair(matrix, ("x", "y"))

            assert (result.first_item_id, result.second_item_id) == expected_pair, case
            assert result.distance == pytest.approx(expected_distance)


@pytest.mark.parametrize(
    "matrix, criteria",
    [
        (_matrix([("a", 1, 1)]), ("x", "y")),
        (_matrix([("a", 1, 1), ("b", 2, 2)]), ("x",)),
        (_matrix([("a", 1, 1), ("b", 2, 2)]), ("x", "x")),
        (_matrix([("a", 1, 1), ("b", 2, 2)]), ("x", "missing")),
    ],
)
def test_closest_pair_rejects_invalid_inputs(matrix: ScoringMatrix, criteria: tuple[str, ...]) -> None:
    with pytest.raises(ClosestPairError):
        closest_pair(matrix, criteria)  # type: ignore[arg-type]


@pytest.mark.parametrize("criteria", [None, "xy", {"x", "y"}, 42])
def test_closest_pair_rejects_invalid_criterion_container(criteria: object) -> None:
    with pytest.raises(ClosestPairError):
        closest_pair(
            _matrix([("a", 1, 1), ("b", 2, 2)]),
            criteria,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("bad_value", [True, math.nan, math.inf, -math.inf, "1"])
def test_closest_pair_rejects_non_finite_or_non_numeric_values(
    bad_value: object,
) -> None:
    matrix = _matrix([("a", 1, 1), ("b", 2, 2)])
    matrix.items[0].values["x"] = bad_value  # type: ignore[assignment]

    with pytest.raises(ClosestPairError, match="números finitos"):
        closest_pair(matrix, ("x", "y"))


def test_closest_pair_rejects_missing_item_value() -> None:
    matrix = _matrix([("a", 1, 1), ("b", 2, 2)])
    del matrix.items[0].values["x"]

    with pytest.raises(ClosestPairError, match="sem valor"):
        closest_pair(matrix, ("x", "y"))
