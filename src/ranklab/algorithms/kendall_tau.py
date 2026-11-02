"""Kendall tau-b para rankings com empates."""

from __future__ import annotations

from dataclasses import dataclass

from ranklab.domain.models import Ranking


class KendallTauError(ValueError):
    pass


@dataclass(frozen=True)
class KendallTauB:
    item_count: int
    concordant_pair_count: int
    discordant_pair_count: int
    ties_first_only: int
    ties_second_only: int
    ties_both: int
    tau_b: float


def compare_rankings_tau_b(first: Ranking, second: Ranking) -> KendallTauB:
    """Compara os mesmos itens com a convenção tau-b e denominador zero = 0."""
    if not isinstance(first, Ranking) or not isinstance(second, Ranking):
        raise KendallTauError("os rankings devem ser objetos Ranking")
    first_by_id = {item.item_id: item for item in first.items}
    second_by_id = {item.item_id: item for item in second.items}
    if len(first_by_id) != len(first.items) or len(second_by_id) != len(second.items):
        raise KendallTauError("item_id duplicado")
    if set(first_by_id) != set(second_by_id):
        raise KendallTauError("os rankings devem conter exatamente os mesmos item_ids")
    if any(not isinstance(item.position, int) or item.position < 1 for item in first.items + second.items):
        raise KendallTauError("posições devem ser inteiros positivos")
    concordant = discordant = first_only = second_only = both = 0
    ids = sorted(first_by_id, key=lambda item_id: first_by_id[item_id].position)
    coordinates = {position: index + 1 for index, position in enumerate(
        sorted({second_by_id[item_id].position for item_id in ids})
    )}
    tree = [0] * (len(coordinates) + 1)

    def add(index: int) -> None:
        while index < len(tree):
            tree[index] += 1
            index += index & -index

    def prefix(index: int) -> int:
        total = 0
        while index:
            total += tree[index]
            index -= index & -index
        return total

    offset = 0
    while offset < len(ids):
        end = offset + 1
        first_position = first_by_id[ids[offset]].position
        while end < len(ids) and first_by_id[ids[end]].position == first_position:
            end += 1
        group = ids[offset:end]
        for index, left_id in enumerate(group):
            left_coordinate = coordinates[second_by_id[left_id].position]
            for right_id in group[index + 1:]:
                right_coordinate = coordinates[second_by_id[right_id].position]
                if left_coordinate == right_coordinate:
                    both += 1
                else:
                    first_only += 1
        prior_count = offset
        for item_id in group:
            coordinate = coordinates[second_by_id[item_id].position]
            less = prefix(coordinate - 1)
            equal = prefix(coordinate) - less
            greater = prior_count - less - equal
            concordant += less
            discordant += greater
            second_only += equal
        for item_id in group:
            add(coordinates[second_by_id[item_id].position])
        offset = end
    denominator = ((concordant + discordant + first_only) *
                   (concordant + discordant + second_only)) ** 0.5
    tau = (concordant - discordant) / denominator if denominator else 0.0
    return KendallTauB(len(ids), concordant, discordant, first_only, second_only, both, tau)


compare_rankings_with_ties = compare_rankings_tau_b
