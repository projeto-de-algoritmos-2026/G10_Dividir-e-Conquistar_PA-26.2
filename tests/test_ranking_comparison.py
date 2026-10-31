"""Testes da comparação de rankings por contagem de inversões."""

from __future__ import annotations

import pytest

from ranklab.algorithms import (
    PAIR_EXPLANATION_ITEM_LIMIT,
    RankingComparison,
    RankingComparisonError,
    compare_rankings,
)
from ranklab.domain.models import Ranking, RankingItem


def _ranking(
    ranking_id: str,
    ordered_ids: list[str],
    *,
    physical_order: list[int] | None = None,
) -> Ranking:
    items = [
        RankingItem(item_id=item_id, position=position)
        for position, item_id in enumerate(ordered_ids, start=1)
    ]
    if physical_order is not None:
        items = [items[index] for index in physical_order]
    return Ranking(
        ranking_id=ranking_id,
        name=ranking_id,
        origin="teste",
        items=tuple(items),
    )


def _pair_set(result: RankingComparison) -> set[tuple[str, str]]:
    pairs = result.discordant_pairs
    assert pairs is not None
    return {
        (pair.earlier_in_first, pair.later_in_first)
        for pair in pairs
    }


def test_identical_rankings_have_no_discordant_pairs() -> None:
    first = _ranking("first", ["a", "b", "c", "d"])
    second = _ranking("second", ["a", "b", "c", "d"])

    result = compare_rankings(first, second)

    assert result.item_count == 4
    assert result.possible_pair_count == 6
    assert result.discordant_pair_count == 0
    assert result.normalized_distance == 0.0
    assert result.discordant_pairs == ()


def test_reverse_order_counts_and_explains_every_pair() -> None:
    first = _ranking("first", ["a", "b", "c", "d"])
    second = _ranking("second", ["d", "c", "b", "a"])

    result = compare_rankings(first, second)

    assert result.discordant_pair_count == 6
    assert result.possible_pair_count == 6
    assert result.normalized_distance == 1.0
    assert _pair_set(result) == {
        ("a", "b"),
        ("a", "c"),
        ("a", "d"),
        ("b", "c"),
        ("b", "d"),
        ("c", "d"),
    }
    assert result.discordant_pairs is not None
    assert len(result.discordant_pairs) == result.discordant_pair_count


def test_partial_divergence_lists_exact_pairs() -> None:
    first = _ranking("first", ["a", "b", "c", "d"])
    second = _ranking("second", ["b", "a", "d", "c"])

    result = compare_rankings(first, second)

    assert result.discordant_pair_count == 2
    assert result.possible_pair_count == 6
    assert result.normalized_distance == pytest.approx(2 / 6)
    assert _pair_set(result) == {("a", "b"), ("c", "d")}


def test_single_item_uses_zero_distance_convention() -> None:
    result = compare_rankings(
        _ranking("first", ["only"]),
        _ranking("second", ["only"]),
    )

    assert result.item_count == 1
    assert result.possible_pair_count == 0
    assert result.discordant_pair_count == 0
    assert result.normalized_distance == 0.0
    assert result.discordant_pairs == ()


def test_physical_tuple_order_does_not_define_ranking_order() -> None:
    first = _ranking("first", ["a", "b", "c"], physical_order=[2, 0, 1])
    second = _ranking("second", ["b", "a", "c"], physical_order=[1, 2, 0])

    result = compare_rankings(first, second)

    assert result.discordant_pair_count == 1
    assert _pair_set(result) == {("a", "b")}


def test_pair_explanations_are_included_at_item_limit() -> None:
    item_ids = [f"item-{index:03d}" for index in range(PAIR_EXPLANATION_ITEM_LIMIT)]

    result = compare_rankings(
        _ranking("first", item_ids),
        _ranking("second", list(reversed(item_ids))),
    )

    assert result.discordant_pair_count == 4_950
    assert result.discordant_pairs is not None
    assert len(result.discordant_pairs) == 4_950


def test_pair_explanations_are_omitted_above_item_limit() -> None:
    count = PAIR_EXPLANATION_ITEM_LIMIT + 1
    item_ids = [f"item-{index:03d}" for index in range(count)]

    result = compare_rankings(
        _ranking("first", item_ids),
        _ranking("second", list(reversed(item_ids))),
    )

    assert result.discordant_pair_count == 5_050
    assert result.normalized_distance == 1.0
    assert result.discordant_pairs is None


def test_different_item_sets_name_both_sides() -> None:
    first = _ranking("first", ["shared", "only-first"])
    second = _ranking("second", ["shared", "only-second"])

    with pytest.raises(RankingComparisonError) as exc_info:
        compare_rankings(first, second)

    message = str(exc_info.value)
    assert "apenas no primeiro" in message
    assert "only-first" in message
    assert "apenas no segundo" in message
    assert "only-second" in message


@pytest.mark.parametrize(
    ("items", "message_fragment"),
    [
        ((), "ao menos um item"),
        (
            (
                RankingItem("a", 1),
                RankingItem("a", 2),
            ),
            "item_id duplicado",
        ),
        (
            (
                RankingItem("a", 1),
                RankingItem("b", 1),
            ),
            "posição duplicada/empate",
        ),
        (
            (
                RankingItem("a", 1),
                RankingItem("b", 3),
            ),
            "intervalo 1..2",
        ),
        (
            (
                RankingItem("", 1),
            ),
            "item_id deve ser uma string não vazia",
        ),
        (
            (
                RankingItem("a", True),
            ),
            "position deve ser um inteiro",
        ),
    ],
)
def test_invalid_ranking_is_rejected(
    items: tuple[RankingItem, ...],
    message_fragment: str,
) -> None:
    invalid = Ranking("invalid", "Invalid", "teste", items)
    valid = _ranking("valid", ["a"])

    with pytest.raises(RankingComparisonError, match=message_fragment):
        compare_rankings(invalid, valid)
