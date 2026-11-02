"""Par de perfis mais próximo em exatamente duas dimensões."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ranklab.algorithms.tracing import (
    TRACE_ITEM_LIMIT,
    TraceStep,
    TracedResult,
    available_trace,
    omitted_trace,
)
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
    if math.isclose(candidate[0], current[0], rel_tol=1e-12, abs_tol=1e-15):
        if _pair_ids(candidate[1], candidate[2]) < _pair_ids(current[1], current[2]):
            return candidate
    elif candidate[0] < current[0]:
        return candidate
    return current


def _point_state(point: _Point) -> dict[str, object]:
    return {"item_id": point.item_id, "x": point.x, "y": point.y}


def _result_state(
    result: tuple[float, _Point, _Point] | None,
) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "distance": result[0],
        "item_ids": list(_pair_ids(result[1], result[2])),
    }


def _brute_force(
    points: list[_Point],
    trace: list[TraceStep] | None = None,
    depth: int = 0,
) -> tuple[float, _Point, _Point] | None:
    best = None
    for index, first in enumerate(points):
        for second in points[index + 1 :]:
            best = _better((_distance(first, second), first, second), best)
    if trace is not None:
        trace.append(
            TraceStep(
                "base_case",
                depth,
                "A subcoleção pequena foi comparada diretamente.",
                {
                    "points": [_point_state(point) for point in points],
                    "best": _result_state(best),
                },
            )
        )
    return best


def _closest(
    by_x: list[_Point],
    by_y: list[_Point],
    trace: list[TraceStep] | None = None,
    depth: int = 0,
) -> tuple[float, _Point, _Point] | None:
    if len(by_x) <= 3:
        return _brute_force(by_x, trace, depth)

    middle = len(by_x) // 2
    left_x = by_x[:middle]
    right_x = by_x[middle:]
    left_ids = {point.item_id for point in left_x}
    left_y = [point for point in by_y if point.item_id in left_ids]
    right_y = [point for point in by_y if point.item_id not in left_ids]

    split_x = right_x[0].x
    if trace is not None:
        trace.append(
            TraceStep(
                "divide",
                depth,
                "Os pontos foram divididos pela coordenada x normalizada.",
                {
                    "split_x": split_x,
                    "left": [_point_state(point) for point in left_x],
                    "right": [_point_state(point) for point in right_x],
                },
            )
        )

    left_best = _closest(left_x, left_y, trace, depth + 1)
    right_best = _closest(right_x, right_y, trace, depth + 1)
    best = _better(left_best, right_best)
    if best is None:
        return None

    distance = best[0]
    strip = [
        point
        for point in by_y
        if abs(point.x - split_x) <= distance
        or math.isclose(
            abs(point.x - split_x), distance, rel_tol=1e-12, abs_tol=1e-15
        )
    ]
    for index, first in enumerate(strip):
        for second in strip[index + 1 : index + 8]:
            best = _better((_distance(first, second), first, second), best)
    if trace is not None:
        trace.append(
            TraceStep(
                "combine",
                depth,
                "O melhor delta dos dois lados definiu a faixa central, que foi examinada para combinar os resultados.",
                {
                    "split_x": split_x,
                    "left_best": _result_state(left_best),
                    "right_best": _result_state(right_best),
                    "delta": distance,
                    "strip": [_point_state(point) for point in strip],
                    "best": _result_state(best),
                },
            )
        )
    return best


def _normalize(value: float, minimum: float, maximum: float, direction: Direction) -> float:
    if maximum == minimum:
        return 0.0
    normalized = (value - minimum) / (maximum - minimum)
    return normalized if direction is Direction.HIGHER_IS_BETTER else 1.0 - normalized


def _closest_pair(
    matrix: ScoringMatrix,
    criterion_ids: tuple[str, str] | list[str],
    trace: list[TraceStep] | None,
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
    if not isinstance(criterion_ids, (tuple, list)):
        raise ClosestPairError(
            "criterion_ids deve ser uma tupla ou lista com dois critérios"
        )
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
    result = _closest(by_x, by_y, trace)
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


def closest_pair(
    matrix: ScoringMatrix,
    criterion_ids: tuple[str, str] | list[str],
) -> ClosestPair:
    """Encontra o par mais próximo sem materializar o passo a passo."""

    return _closest_pair(matrix, criterion_ids, None)


def trace_closest_pair(
    matrix: ScoringMatrix,
    criterion_ids: tuple[str, str] | list[str],
) -> TracedResult[ClosestPair]:
    """Encontra o par e registra divisões, deltas e faixas centrais."""

    item_count = len(matrix.items) if isinstance(matrix, ScoringMatrix) else 0
    if item_count > TRACE_ITEM_LIMIT:
        return TracedResult(
            closest_pair(matrix, criterion_ids),
            omitted_trace("closest_pair", item_count),
        )
    steps: list[TraceStep] = []
    result = _closest_pair(matrix, criterion_ids, steps)
    return TracedResult(
        result,
        available_trace("closest_pair", item_count, steps),
    )
