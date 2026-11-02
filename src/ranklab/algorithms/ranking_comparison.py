"""Comparação de rankings estritos por contagem de inversões.

O primeiro ranking é convertido na sequência das posições que seus itens
ocupam no segundo ranking. Cada inversão dessa sequência corresponde a um
par de itens cuja ordem relativa diverge entre os rankings.
"""

from __future__ import annotations

from dataclasses import dataclass

from ranklab.domain.models import Ranking, RankingItem
from ranklab.algorithms.tracing import (
    TRACE_ITEM_LIMIT,
    TraceStep,
    TracedResult,
    available_trace,
    omitted_trace,
)

PAIR_EXPLANATION_ITEM_LIMIT = 100
"""Maior número de itens para o qual todos os pares são materializados."""


class RankingComparisonError(ValueError):
    """Indica que um ranking é inválido ou que dois rankings são incompatíveis."""


@dataclass(frozen=True)
class DiscordantPair:
    """Par cuja ordem relativa muda entre os rankings.

    ``earlier_in_first`` aparece antes de ``later_in_first`` no primeiro
    ranking; no segundo ranking, a ordem é a oposta.
    """

    earlier_in_first: str
    later_in_first: str


@dataclass(frozen=True)
class RankingComparison:
    """Resultado completo da comparação entre dois rankings estritos."""

    item_count: int
    possible_pair_count: int
    discordant_pair_count: int
    normalized_distance: float
    discordant_pairs: tuple[DiscordantPair, ...] | None


@dataclass(frozen=True)
class _MappedItem:
    """Item do primeiro ranking anotado com sua posição no segundo."""

    second_position: int
    item_id: str


def _ordered_items(ranking: Ranking, label: str) -> tuple[RankingItem, ...]:
    """Valida os invariantes relevantes e ordena os itens por posição."""

    if not isinstance(ranking, Ranking):
        raise RankingComparisonError(f"{label} deve ser um objeto Ranking")

    items = ranking.items
    if not isinstance(items, tuple) or not items:
        raise RankingComparisonError(f"{label} deve conter ao menos um item")

    seen_ids: set[str] = set()
    seen_positions: set[int] = set()

    for index, item in enumerate(items):
        item_label = f"{label}, items[{index}]"
        if not isinstance(item, RankingItem):
            raise RankingComparisonError(f"{item_label} deve ser um RankingItem")

        if not isinstance(item.item_id, str) or not item.item_id:
            raise RankingComparisonError(
                f"{item_label}: item_id deve ser uma string não vazia"
            )
        if item.item_id in seen_ids:
            raise RankingComparisonError(
                f"{label}: item_id duplicado: {item.item_id!r}"
            )
        seen_ids.add(item.item_id)

        if not isinstance(item.position, int) or isinstance(item.position, bool):
            raise RankingComparisonError(
                f"{item_label}: position deve ser um inteiro"
            )
        if item.position in seen_positions:
            raise RankingComparisonError(
                f"{label}: posição duplicada/empate: {item.position}"
            )
        seen_positions.add(item.position)

    expected_positions = set(range(1, len(items) + 1))
    if seen_positions != expected_positions:
        raise RankingComparisonError(
            f"{label}: posições devem formar exatamente o intervalo "
            f"1..{len(items)}"
        )

    return tuple(sorted(items, key=lambda item: item.position))


def _sort_and_count(
    entries: list[_MappedItem],
    buffer: list[_MappedItem],
    start: int,
    end: int,
    pairs: list[DiscordantPair] | None,
    trace: list[TraceStep] | None = None,
    depth: int = 0,
    parent_id: int | None = None,
    node_counter: list[int] | None = None,
) -> int:
    """Ordena ``entries[start:end]`` e devolve sua contagem de inversões."""

    node_id: int | None = None
    if trace is not None and node_counter is not None:
        node_id = node_counter[0]
        node_counter[0] += 1

    if end - start <= 1:
        if trace is not None:
            trace.append(
                TraceStep(
                    "leaf",
                    depth,
                    "A sublista tem um único item e já está ordenada.",
                    {
                        "node_id": node_id,
                        "parent_id": parent_id,
                        "items": [entry.item_id for entry in entries[start:end]],
                        "positions": [
                            entry.second_position for entry in entries[start:end]
                        ],
                    },
                )
            )
        return 0

    middle = (start + end) // 2
    if trace is not None:
        trace.append(
            TraceStep(
                "divide",
                depth,
                "A sequência foi dividida em duas metades para ordenar e contar inversões.",
                {
                    "node_id": node_id,
                    "parent_id": parent_id,
                    "items": [entry.item_id for entry in entries[start:end]],
                    "positions": [
                        entry.second_position for entry in entries[start:end]
                    ],
                    "left_items": [
                        entry.item_id for entry in entries[start:middle]
                    ],
                    "right_items": [
                        entry.item_id for entry in entries[middle:end]
                    ],
                },
            )
        )
    inversion_count = _sort_and_count(
        entries,
        buffer,
        start,
        middle,
        pairs,
        trace,
        depth + 1,
        node_id,
        node_counter,
    )
    inversion_count += _sort_and_count(
        entries,
        buffer,
        middle,
        end,
        pairs,
        trace,
        depth + 1,
        node_id,
        node_counter,
    )
    before_merge = inversion_count

    left = start
    right = middle
    output = start

    while left < middle and right < end:
        if entries[left].second_position <= entries[right].second_position:
            buffer[output] = entries[left]
            left += 1
        else:
            right_item = entries[right]
            inversion_count += middle - left

            if pairs is not None:
                for inverted_left in range(left, middle):
                    pairs.append(
                        DiscordantPair(
                            earlier_in_first=entries[inverted_left].item_id,
                            later_in_first=right_item.item_id,
                        )
                    )

            buffer[output] = right_item
            right += 1
        output += 1

    while left < middle:
        buffer[output] = entries[left]
        left += 1
        output += 1

    while right < end:
        buffer[output] = entries[right]
        right += 1
        output += 1

    for index in range(start, end):
        entries[index] = buffer[index]

    if trace is not None:
        added = inversion_count - before_merge
        trace.append(
            TraceStep(
                "merge",
                depth,
                (
                    f"As metades foram combinadas e acrescentaram {added} "
                    f"{'inversão' if added == 1 else 'inversões'}."
                ),
                {
                    "node_id": node_id,
                    "parent_id": parent_id,
                    "merged_items": [
                        entry.item_id for entry in entries[start:end]
                    ],
                    "merged_positions": [
                        entry.second_position for entry in entries[start:end]
                    ],
                    "inversions_added": added,
                    "subtree_inversions": inversion_count,
                },
            )
        )

    return inversion_count


def _compare_rankings(
    first: Ranking,
    second: Ranking,
    trace: list[TraceStep] | None,
) -> RankingComparison:
    """Compara dois rankings completos e estritos dos mesmos itens.

    A contagem usa merge sort em ``O(n log n)`` tempo e ``O(n)`` espaço
    auxiliar. Para no máximo :data:`PAIR_EXPLANATION_ITEM_LIMIT` itens, os
    pares discordantes também são retornados. Materializar ``k`` pares exige
    ``O(k)`` tempo e espaço de saída adicionais.

    Levanta :class:`RankingComparisonError` se algum ranking não respeitar os
    invariantes estritos ou se os conjuntos de itens forem diferentes.
    """

    first_items = _ordered_items(first, "primeiro ranking")
    second_items = _ordered_items(second, "segundo ranking")

    first_ids = {item.item_id for item in first_items}
    second_ids = {item.item_id for item in second_items}
    if first_ids != second_ids:
        only_first = sorted(first_ids - second_ids)
        only_second = sorted(second_ids - first_ids)
        details: list[str] = []
        if only_first:
            details.append(f"apenas no primeiro: {only_first}")
        if only_second:
            details.append(f"apenas no segundo: {only_second}")
        raise RankingComparisonError(
            "os rankings devem conter exatamente os mesmos item_ids; "
            + "; ".join(details)
        )

    second_positions = {
        item.item_id: item.position
        for item in second_items
    }
    entries = [
        _MappedItem(
            second_position=second_positions[item.item_id],
            item_id=item.item_id,
        )
        for item in first_items
    ]

    collect_pairs = len(entries) <= PAIR_EXPLANATION_ITEM_LIMIT
    pairs: list[DiscordantPair] | None = [] if collect_pairs else None
    buffer = entries.copy()
    discordant_pair_count = _sort_and_count(
        entries,
        buffer,
        0,
        len(entries),
        pairs,
        trace,
        node_counter=[0] if trace is not None else None,
    )

    possible_pair_count = len(entries) * (len(entries) - 1) // 2
    normalized_distance = (
        discordant_pair_count / possible_pair_count
        if possible_pair_count
        else 0.0
    )

    return RankingComparison(
        item_count=len(entries),
        possible_pair_count=possible_pair_count,
        discordant_pair_count=discordant_pair_count,
        normalized_distance=normalized_distance,
        discordant_pairs=tuple(pairs) if pairs is not None else None,
    )


def compare_rankings(first: Ranking, second: Ranking) -> RankingComparison:
    """Compara dois rankings sem materializar o passo a passo."""

    return _compare_rankings(first, second, None)


def trace_ranking_comparison(
    first: Ranking,
    second: Ranking,
) -> TracedResult[RankingComparison]:
    """Compara rankings e registra a árvore do merge sort quando permitido."""

    item_count = len(first.items) if isinstance(first, Ranking) else 0
    if item_count > TRACE_ITEM_LIMIT:
        return TracedResult(
            compare_rankings(first, second),
            omitted_trace("merge_sort_inversions", item_count),
        )
    steps: list[TraceStep] = []
    result = _compare_rankings(first, second, steps)
    return TracedResult(
        result,
        available_trace("merge_sort_inversions", result.item_count, steps),
    )
