"""Seleção determinística pela mediana das medianas.

O algoritmo usa índices de ordem iniciados em 1 (``k=1`` é o menor
elemento). Duplicatas são válidas e a seleção é feita sobre os valores da
chave, sem ordenar a coleção inteira.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeVar

from ranklab.algorithms.tracing import (
    TRACE_ITEM_LIMIT,
    TraceStep,
    TracedResult,
    available_trace,
    omitted_trace,
)

T = TypeVar("T")
K = TypeVar("K")


class SelectionError(ValueError):
    """Indica uma coleção, ordem ou percentil inválido."""


@dataclass(frozen=True)
class SelectionResult:
    """Elemento selecionado e a ordem solicitada."""

    value: object
    order: int
    percentile: float | None = None


def percentile_to_order(percentile: float, item_count: int) -> int:
    """Converte percentil [0, 100] para a ordem estatística 1-based.

    Usa a regra de posto mais próximo para seleção: ``ceil(p*n/100)``,
    limitando o percentil zero ao primeiro elemento.
    """

    if isinstance(percentile, bool) or not isinstance(percentile, (int, float)):
        raise SelectionError("percentile deve ser um número")
    if not math.isfinite(float(percentile)) or not 0 <= percentile <= 100:
        raise SelectionError("percentile deve estar no intervalo [0, 100]")
    if not isinstance(item_count, int) or isinstance(item_count, bool) or item_count < 1:
        raise SelectionError("item_count deve ser um inteiro positivo")
    return max(1, math.ceil(float(percentile) * item_count / 100))


def _median_of_medians(
    items: list[T],
    key: Callable[[T], K],
    trace: list[TraceStep] | None = None,
    depth: int = 0,
) -> T:
    if len(items) <= 5:
        items.sort(key=key)
        if trace is not None:
            trace.append(
                TraceStep(
                    "group_medians",
                    depth,
                    "O grupo final foi ordenado e sua mediana foi escolhida como pivô.",
                    {
                        "groups": [[key(item) for item in items]],
                        "medians": [key(items[len(items) // 2])],
                    },
                )
            )
        return items[len(items) // 2]

    medians: list[T] = []
    groups: list[list[K]] | None = [] if trace is not None else None
    for start in range(0, len(items), 5):
        group = items[start : start + 5]
        group.sort(key=key)
        if groups is not None:
            groups.append([key(item) for item in group])
        medians.append(group[len(group) // 2])
    if trace is not None:
        trace.append(
            TraceStep(
                "group_medians",
                depth,
                "A coleção foi separada em grupos de até cinco e a mediana de cada grupo foi coletada.",
                {
                    "groups": groups,
                    "medians": [key(item) for item in medians],
                },
            )
        )
    return _select(medians, len(medians) // 2, key, trace, depth + 1)


def _select(
    items: list[T],
    target: int,
    key: Callable[[T], K],
    trace: list[TraceStep] | None = None,
    depth: int = 0,
) -> T:
    if len(items) <= 5:
        items.sort(key=key)
        if trace is not None:
            trace.append(
                TraceStep(
                    "base_case",
                    depth,
                    "A subcoleção pequena foi ordenada e o elemento da ordem local foi selecionado.",
                    {
                        "values": [key(item) for item in items],
                        "target_order": target + 1,
                        "selected": key(items[target]),
                    },
                )
            )
        return items[target]

    pivot = key(_median_of_medians(items, key, trace, depth))
    lower = [item for item in items if key(item) < pivot]
    equal = [item for item in items if key(item) == pivot]
    higher = [item for item in items if key(item) > pivot]

    if target < len(lower):
        next_partition = "lower"
    elif target < len(lower) + len(equal):
        next_partition = "equal"
    else:
        next_partition = "higher"
    if trace is not None:
        trace.append(
            TraceStep(
                "partition",
                depth,
                (
                    "O pivô dividiu a coleção em valores menores, iguais e maiores; "
                    f"a busca segue pela partição {next_partition}."
                ),
                {
                    "values": [key(item) for item in items],
                    "target_order": target + 1,
                    "pivot": pivot,
                    "lower": [key(item) for item in lower],
                    "equal": [key(item) for item in equal],
                    "higher": [key(item) for item in higher],
                    "next_partition": next_partition,
                },
            )
        )

    if target < len(lower):
        return _select(lower, target, key, trace, depth + 1)
    if target < len(lower) + len(equal):
        return equal[0]
    return _select(
        higher,
        target - len(lower) - len(equal),
        key,
        trace,
        depth + 1,
    )


def _select_k(
    items: Sequence[T],
    k: int,
    key: Callable[[T], K] | None,
    trace: list[TraceStep] | None,
) -> SelectionResult:
    if not items:
        raise SelectionError("a coleção não pode ser vazia")
    if isinstance(k, bool) or not isinstance(k, int):
        raise SelectionError("k deve ser um inteiro 1-based")
    if not 1 <= k <= len(items):
        raise SelectionError(f"k deve estar no intervalo [1, {len(items)}]")
    selected_key = key or (lambda item: item)  # type: ignore[return-value]
    value = _select(list(items), k - 1, selected_key, trace)
    return SelectionResult(value=value, order=k)


def select_k(
    items: Sequence[T],
    k: int,
    *,
    key: Callable[[T], K] | None = None,
) -> SelectionResult:
    """Retorna o elemento de ordem ``k`` em uma coleção não ordenada.

    ``k`` é 1-based, duplicatas são consideradas normalmente e a entrada não
    é modificada. O custo é O(n) no pior caso, com grupos de no máximo cinco.
    """

    return _select_k(items, k, key, None)


def select_percentile(
    items: Sequence[T],
    percentile: float,
    *,
    key: Callable[[T], K] | None = None,
) -> SelectionResult:
    """Seleciona o posto correspondente a um percentil entre 0 e 100."""

    if not items:
        raise SelectionError("a coleção não pode ser vazia")
    order = percentile_to_order(percentile, len(items))
    result = select_k(items, order, key=key)
    return SelectionResult(
        value=result.value,
        order=result.order,
        percentile=float(percentile),
    )


def trace_select_k(
    items: Sequence[T],
    k: int,
    *,
    key: Callable[[T], K] | None = None,
) -> TracedResult[SelectionResult]:
    """Seleciona a ordem e registra grupos, pivôs e partições."""

    if len(items) > TRACE_ITEM_LIMIT:
        return TracedResult(
            select_k(items, k, key=key),
            omitted_trace("median_of_medians", len(items)),
        )
    steps: list[TraceStep] = []
    result = _select_k(items, k, key, steps)
    return TracedResult(
        result,
        available_trace("median_of_medians", len(items), steps),
    )


def trace_select_percentile(
    items: Sequence[T],
    percentile: float,
    *,
    key: Callable[[T], K] | None = None,
) -> TracedResult[SelectionResult]:
    """Seleciona um percentil e registra a mesma execução por ordem."""

    if not items:
        raise SelectionError("a coleção não pode ser vazia")
    order = percentile_to_order(percentile, len(items))
    traced = trace_select_k(items, order, key=key)
    result = SelectionResult(
        value=traced.result.value,
        order=order,
        percentile=float(percentile),
    )
    return TracedResult(result, traced.trace)
