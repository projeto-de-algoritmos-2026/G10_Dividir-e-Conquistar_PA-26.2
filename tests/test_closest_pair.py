from __future__ import annotations

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


def test_closest_pair_normalizes_scales_and_respects_direction() -> None:
    result = closest_pair(
        _matrix([("a", 0, 1000), ("b", 10, 990), ("c", 100, 0)]),
        ("x", "y"),
    )

    assert (result.first_item_id, result.second_item_id) == ("a", "b")
    assert result.distance == pytest.approx((0.1**2 + 0.01**2) ** 0.5)
    assert result.criterion_ids == ("x", "y")


def test_closest_pair_uses_lexicographic_tie_break() -> None:
    result = closest_pair(
        _matrix([("z", 0, 0), ("b", 1, 1), ("a", 2, 2), ("c", 3, 3)]),
        ("x", "y"),
    )

    assert (result.first_item_id, result.second_item_id) == ("a", "b")


def test_constant_dimension_is_projected_to_zero() -> None:
    result = closest_pair(
        _matrix([("a", 0, 5), ("b", 10, 5), ("c", 20, 5)]),
        ("x", "y"),
    )

    assert result.distance == pytest.approx(0.5)
    assert (result.first_item_id, result.second_item_id) == ("a", "b")


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
