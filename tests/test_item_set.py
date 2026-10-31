"""Testes para assert_same_item_set."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from ranklab.domain.models import Ranking, RankingItem
from ranklab.io.errors import RankLabError
from ranklab.io.readers import assert_same_item_set, load_ranking

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def _make_ranking(ranking_id: str, item_ids: list[str]) -> Ranking:
    items = tuple(
        RankingItem(item_id=iid, position=pos)
        for pos, iid in enumerate(item_ids, start=1)
    )
    return Ranking(ranking_id=ranking_id, name="n", origin="o", items=items)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_identical_sets_no_error() -> None:
    a = _make_ranking("r-a", ["x", "y", "z"])
    b = _make_ranking("r-b", ["z", "x", "y"])
    assert_same_item_set(a, b)  # should not raise


def test_same_ranking_against_itself() -> None:
    r = load_ranking(EXAMPLES_DIR / "ranking.json")
    assert_same_item_set(r, r)  # should not raise


# ---------------------------------------------------------------------------
# Error path
# ---------------------------------------------------------------------------

def test_item_only_in_a_raises() -> None:
    a = _make_ranking("r-a", ["x", "y", "extra"])
    b = _make_ranking("r-b", ["x", "y"])
    with pytest.raises(RankLabError) as exc_info:
        assert_same_item_set(a, b)
    assert "extra" in str(exc_info.value)
    assert "r-a" in str(exc_info.value)


def test_item_only_in_b_raises() -> None:
    a = _make_ranking("r-a", ["x", "y"])
    b = _make_ranking("r-b", ["x", "y", "extra"])
    with pytest.raises(RankLabError) as exc_info:
        assert_same_item_set(a, b)
    assert "extra" in str(exc_info.value)
    assert "r-b" in str(exc_info.value)


def test_completely_different_sets() -> None:
    a = _make_ranking("r-a", ["p", "q"])
    b = _make_ranking("r-b", ["x", "y"])
    with pytest.raises(RankLabError) as exc_info:
        assert_same_item_set(a, b)
    err = str(exc_info.value)
    assert "p" in err or "q" in err
    assert "x" in err or "y" in err
