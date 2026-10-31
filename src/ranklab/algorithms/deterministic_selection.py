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


def _median_of_medians(items: list[T], key: Callable[[T], K]) -> T:
    if len(items) <= 5:
        items.sort(key=key)
        return items[len(items) // 2]

    medians: list[T] = []
    for start in range(0, len(items), 5):
        group = items[start : start + 5]
        group.sort(key=key)
        medians.append(group[len(group) // 2])
    return _select(medians, len(medians) // 2, key)


def _select(items: list[T], target: int, key: Callable[[T], K]) -> T:
    if len(items) <= 5:
        items.sort(key=key)
        return items[target]

    pivot = key(_median_of_medians(items, key))
    lower = [item for item in items if key(item) < pivot]
    equal = [item for item in items if key(item) == pivot]
    higher = [item for item in items if key(item) > pivot]

    if target < len(lower):
        return _select(lower, target, key)
    if target < len(lower) + len(equal):
        return equal[0]
    return _select(higher, target - len(lower) - len(equal), key)


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

    if not items:
        raise SelectionError("a coleção não pode ser vazia")
    if isinstance(k, bool) or not isinstance(k, int):
        raise SelectionError("k deve ser um inteiro 1-based")
    if not 1 <= k <= len(items):
        raise SelectionError(f"k deve estar no intervalo [1, {len(items)}]")
    selected_key = key or (lambda item: item)  # type: ignore[return-value]
    value = _select(list(items), k - 1, selected_key)
    return SelectionResult(value=value, order=k)


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
