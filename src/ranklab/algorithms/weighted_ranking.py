"""Ranking multicritério por normalização min-max e soma ponderada."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from ranklab.domain.models import (
    Criterion,
    Direction,
    MatrixItem,
    ScoringMatrix,
)


class WeightedRankingError(ValueError):
    """Indica uma matriz ou um conjunto de pesos inválido para agregação."""


@dataclass(frozen=True)
class CriterionWeight:
    """Peso informado e peso efetivamente usado para um critério."""

    criterion_id: str
    input_weight: float
    normalized_weight: float


@dataclass(frozen=True)
class AggregatedItem:
    """Item ranqueado com os valores que explicam seu score."""

    item_id: str
    position: int
    normalized_values: dict[str, float]
    score: float


@dataclass(frozen=True)
class AggregatedRanking:
    """Resultado auditável de uma agregação multicritério."""

    matrix_id: str
    weights: tuple[CriterionWeight, ...]
    items: tuple[AggregatedItem, ...]
    normalization: str = "min-max orientada pela direção"
    aggregation: str = "soma ponderada"
    tie_break: str = "score decrescente; item_id lexicográfico crescente"


def _format_ids(ids: set[object]) -> str:
    """Formata IDs em ordem determinística, inclusive se não forem strings."""

    return ", ".join(repr(value) for value in sorted(ids, key=repr))


def _finite_float(value: object, error_message: str) -> float:
    """Converte um número aceito em float sem deixar ``OverflowError`` escapar."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WeightedRankingError(error_message)
    try:
        converted = float(value)
    except (OverflowError, ValueError) as exc:
        raise WeightedRankingError(error_message) from exc
    if not math.isfinite(converted):
        raise WeightedRankingError(error_message)
    return converted


def _validated_matrix(
    matrix: ScoringMatrix,
) -> tuple[tuple[Criterion, ...], tuple[MatrixItem, ...]]:
    if not isinstance(matrix, ScoringMatrix):
        raise WeightedRankingError("matrix deve ser um ScoringMatrix")
    if not matrix.criteria:
        raise WeightedRankingError("matrix deve conter ao menos um critério")
    if not matrix.items:
        raise WeightedRankingError("matrix deve conter ao menos um item")

    criterion_ids: set[str] = set()
    for index, criterion in enumerate(matrix.criteria):
        label = f"criteria[{index}]"
        if not isinstance(criterion, Criterion):
            raise WeightedRankingError(f"{label} deve ser um Criterion")
        if not isinstance(criterion.criterion_id, str) or not criterion.criterion_id:
            raise WeightedRankingError(f"{label}.criterion_id deve ser uma string não vazia")
        if criterion.criterion_id in criterion_ids:
            raise WeightedRankingError(
                f"criterion_id duplicado: {criterion.criterion_id!r}"
            )
        if not isinstance(criterion.direction, Direction):
            raise WeightedRankingError(
                f"{label}.direction deve ser higher_is_better ou lower_is_better"
            )
        criterion_ids.add(criterion.criterion_id)

    item_ids: set[str] = set()
    for index, item in enumerate(matrix.items):
        label = f"items[{index}]"
        if not isinstance(item, MatrixItem):
            raise WeightedRankingError(f"{label} deve ser um MatrixItem")
        if not isinstance(item.item_id, str) or not item.item_id:
            raise WeightedRankingError(f"{label}.item_id deve ser uma string não vazia")
        if item.item_id in item_ids:
            raise WeightedRankingError(f"item_id duplicado: {item.item_id!r}")
        item_ids.add(item.item_id)
        if not isinstance(item.values, dict):
            raise WeightedRankingError(f"{label}.values deve ser um dicionário")

        value_ids = set(item.values)
        missing = criterion_ids - value_ids
        unknown = value_ids - criterion_ids
        if missing:
            raise WeightedRankingError(
                f"{label}.values sem critérios: {_format_ids(set(missing))}"
            )
        if unknown:
            raise WeightedRankingError(
                f"{label}.values contém critérios desconhecidos: "
                f"{_format_ids(set(unknown))}"
            )
        for criterion_id, value in item.values.items():
            _finite_float(
                value,
                f"{label}.values.{criterion_id} deve ser um número finito",
            )

    return matrix.criteria, matrix.items


def _normalized_weights(
    criteria: tuple[Criterion, ...],
    weights: Mapping[str, float],
) -> tuple[dict[str, float], dict[str, float]]:
    if not isinstance(weights, Mapping):
        raise WeightedRankingError("weights deve ser um mapping de criterion_id para peso")

    criterion_ids = {criterion.criterion_id for criterion in criteria}
    weight_ids = set(weights)
    missing = criterion_ids - weight_ids
    unknown = weight_ids - criterion_ids
    if missing:
        raise WeightedRankingError(
            f"pesos ausentes para critérios: {_format_ids(set(missing))}"
        )
    if unknown:
        raise WeightedRankingError(
            f"pesos informados para critérios desconhecidos: "
            f"{_format_ids(set(unknown))}"
        )

    input_weights: dict[str, float] = {}
    for criterion_id in sorted(criterion_ids):
        value = weights[criterion_id]
        numeric_value = _finite_float(
            value,
            f"peso de {criterion_id!r} deve ser um número finito",
        )
        if numeric_value < 0:
            raise WeightedRankingError(
                f"peso de {criterion_id!r} deve ser não negativo"
            )
        input_weights[criterion_id] = numeric_value

    largest = max(input_weights.values())
    if largest <= 0:
        raise WeightedRankingError("a soma dos pesos deve ser maior que zero")

    # Escalar antes de somar evita overflow quando vários pesos finitos estão
    # próximos do maior float representável. A razão final é a mesma de
    # ``weight / sum(weights)``.
    scaled_weights = {
        criterion_id: value / largest
        for criterion_id, value in input_weights.items()
    }
    scaled_total = math.fsum(scaled_weights.values())
    normalized = {
        criterion_id: value / scaled_total
        for criterion_id, value in scaled_weights.items()
    }
    return input_weights, normalized


def _normalize_column(
    values: list[float],
    direction: Direction,
) -> list[float]:
    minimum = min(values)
    maximum = max(values)
    if maximum == minimum:
        return [0.0] * len(values)

    span = maximum - minimum
    if not math.isfinite(span):
        # ``maximum - minimum`` pode transbordar mesmo com duas extremidades
        # finitas. Escalar a coluna preserva a razão min-max e evita o inf.
        scale = max(abs(minimum), abs(maximum))
        scaled_values = [value / scale for value in values]
        scaled_minimum = minimum / scale
        scaled_maximum = maximum / scale
        scaled_span = scaled_maximum - scaled_minimum
        if direction is Direction.HIGHER_IS_BETTER:
            return [
                (value - scaled_minimum) / scaled_span
                for value in scaled_values
            ]
        return [
            (scaled_maximum - value) / scaled_span
            for value in scaled_values
        ]
    if direction is Direction.HIGHER_IS_BETTER:
        return [(value - minimum) / span for value in values]
    return [(maximum - value) / span for value in values]


def aggregate_ranking(
    matrix: ScoringMatrix,
    weights: Mapping[str, float],
) -> AggregatedRanking:
    """Agrega uma matriz válida por min-max orientada e soma ponderada.

    Há exatamente um peso para cada critério. Pesos válidos são normalizados
    para soma 1; colunas constantes são projetadas em zero. O resultado é
    estrito: scores idênticos são desempateados pelo ``item_id``.
    """

    criteria, items = _validated_matrix(matrix)
    input_weights, normalized_weights = _normalized_weights(criteria, weights)

    normalized_by_item: dict[str, dict[str, float]] = {
        item.item_id: {} for item in items
    }
    for criterion in criteria:
        criterion_id = criterion.criterion_id
        values = [float(item.values[criterion_id]) for item in items]
        normalized_values = _normalize_column(values, criterion.direction)
        for item, normalized in zip(items, normalized_values, strict=True):
            normalized_by_item[item.item_id][criterion_id] = normalized

    canonical_ids = sorted(normalized_weights)
    scored = [
        (
            item.item_id,
            math.fsum(
                normalized_weights[criterion_id]
                * normalized_by_item[item.item_id][criterion_id]
                for criterion_id in canonical_ids
            ),
        )
        for item in items
    ]
    scored.sort(key=lambda entry: (-entry[1], entry[0]))

    ranked_items = tuple(
        AggregatedItem(
            item_id=item_id,
            position=position,
            normalized_values=normalized_by_item[item_id],
            score=score,
        )
        for position, (item_id, score) in enumerate(scored, start=1)
    )
    reported_weights = tuple(
        CriterionWeight(
            criterion_id=criterion.criterion_id,
            input_weight=input_weights[criterion.criterion_id],
            normalized_weight=normalized_weights[criterion.criterion_id],
        )
        for criterion in criteria
    )

    return AggregatedRanking(
        matrix_id=matrix.matrix_id,
        weights=reported_weights,
        items=ranked_items,
    )
