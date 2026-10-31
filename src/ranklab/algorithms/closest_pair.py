"""Par de perfis mais próximo em exatamente duas dimensões."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ranklab.domain.models import Direction, ScoringMatrix


class ClosestPairError(ValueError):
    """Indica uma matriz ou seleção de critérios inválida."""


@dataclass(frozen=True)
class ClosestPair:
    """Resultado da proximidade numérica entre dois perfis."""

    first_item_id: str
    second_item_id: str
    distance: float
    criterion_ids: tuple[str, str]
    normalization: str = "min-max orientada pela direção"
    metric: str = "Euclidiana"


@dataclass(frozen=True)
class _Point:
    item_id: str
    x: float
    y: float


def _pair_ids(a: _Point, b: _Point) -> tuple[str, str]:
    return tuple(sorted((a.item_id, b.item_id)))  # type: ignore[return-value]


def _distance(a: _Point, b: _Point) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _better(
    candidate: tuple[float, _Point, _Point] | None,
    current: tuple[float, _Point, _Point] | None,
) -> tuple[float, _Point, _Point] | None:
    if candidate is None:
        return current
    if current is None:
        return candidate
    if candidate[0] < current[0]:
        return candidate
    if math.isclose(candidate[0], current[0], rel_tol=1e-12, abs_tol=1e-15) and _pair_ids(
        candidate[1], candidate[2]
    ) < _pair_ids(current[1], current[2]):
        return candidate
    return current


def _brute_force(points: list[_Point]) -> tuple[float, _Point, _Point] | None:
    best = None
    for index, first in enumerate(points):
        for second in points[index + 1 :]:
            best = _better((_distance(first, second), first, second), best)
    return best


def _closest(
    by_x: list[_Point],
    by_y: list[_Point],
) -> tuple[float, _Point, _Point] | None:
    if len(by_x) <= 3:
        return _brute_force(by_x)

    middle = len(by_x) // 2
    left_x = by_x[:middle]
    right_x = by_x[middle:]
    left_ids = {point.item_id for point in left_x}
    left_y = [point for point in by_y if point.item_id in left_ids]
    right_y = [point for point in by_y if point.item_id not in left_ids]

    best = _better(_closest(left_x, left_y), _closest(right_x, right_y))
    if best is None:
        return None

    distance = best[0]
    split_x = right_x[0].x
    strip = [point for point in by_y if abs(point.x - split_x) <= distance]
    for index, first in enumerate(strip):
        for second in strip[index + 1 : index + 8]:
            best = _better((_distance(first, second), first, second), best)
    return best


def _normalize(value: float, minimum: float, maximum: float, direction: Direction) -> float:
    if maximum == minimum:
        return 0.0
    normalized = (value - minimum) / (maximum - minimum)
    return normalized if direction is Direction.HIGHER_IS_BETTER else 1.0 - normalized


def closest_pair(
    matrix: ScoringMatrix,
    criterion_ids: tuple[str, str] | list[str],
) -> ClosestPair:
    """Encontra o par mais próximo após normalização min-max.

    A divisão e conquista mantém pontos ordenados por x e y e tem custo
    O(n log n). Colunas constantes são projetadas em zero; isso representa que
    elas não distinguem os perfis. Empates retornam o par de IDs
    lexicograficamente menor.
    """

    if not isinstance(matrix, ScoringMatrix):
        raise ClosestPairError("matrix deve ser um ScoringMatrix")
    if len(matrix.items) < 2:
        raise ClosestPairError("são necessários ao menos dois itens")
    if len(criterion_ids) != 2 or criterion_ids[0] == criterion_ids[1]:
        raise ClosestPairError("criterion_ids deve conter exatamente dois critérios distintos")
    criteria = {criterion.criterion_id: criterion for criterion in matrix.criteria}
    if any(criterion_id not in criteria for criterion_id in criterion_ids):
        raise ClosestPairError("os dois critérios devem existir na matriz")

    first_id, second_id = criterion_ids
    try:
        first_values = [item.values[first_id] for item in matrix.items]
        second_values = [item.values[second_id] for item in matrix.items]
    except KeyError as exc:
        raise ClosestPairError(
            f"item sem valor para o critério {exc.args[0]!r}"
        ) from exc
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in (*first_values, *second_values)
    ):
        raise ClosestPairError("os valores dos critérios devem ser números finitos")
    first_min, first_max = min(first_values), max(first_values)
    second_min, second_max = min(second_values), max(second_values)
    first_direction = criteria[first_id].direction
    second_direction = criteria[second_id].direction

    points = [
        _Point(
            item_id=item.item_id,
            x=_normalize(item.values[first_id], first_min, first_max, first_direction),
            y=_normalize(item.values[second_id], second_min, second_max, second_direction),
        )
        for item in matrix.items
    ]
    by_x = sorted(points, key=lambda point: (point.x, point.y, point.item_id))
    by_y = sorted(points, key=lambda point: (point.y, point.x, point.item_id))
    result = _closest(by_x, by_y)
    if result is None:
        raise ClosestPairError("não foi possível encontrar um par")
    distance, first, second = result
    first_item_id, second_item_id = _pair_ids(first, second)
    return ClosestPair(
        first_item_id=first_item_id,
        second_item_id=second_item_id,
        distance=distance,
        criterion_ids=(first_id, second_id),
    )
