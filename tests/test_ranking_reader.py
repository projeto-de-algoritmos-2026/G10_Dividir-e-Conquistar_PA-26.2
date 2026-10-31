"""Testes para o leitor de ranking."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from ranklab.domain.models import Ranking, RankingItem
from ranklab.io.errors import RankLabError
from ranklab.io.readers import load_ranking

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_load_example_ranking() -> None:
    r = load_ranking(EXAMPLES_DIR / "ranking.json")
    assert isinstance(r, Ranking)
    assert r.ranking_id == "fornecedores-2026-a"
    assert r.name == "Avaliação técnica"
    assert r.origin == "exemplo fictício"
    assert len(r.items) == 3


def test_items_sorted_by_position(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [
            {"item_id": "c", "position": 3},
            {"item_id": "a", "position": 1},
            {"item_id": "b", "position": 2},
        ],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    r = load_ranking(f)
    positions = [it.position for it in r.items]
    assert positions == [1, 2, 3]


# ---------------------------------------------------------------------------
# Campos obrigatórios no topo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("missing_field", [
    "format_version", "ranking_id", "name", "origin", "items",
])
def test_missing_top_level_field(tmp_path: Path, missing_field: str) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [{"item_id": "a", "position": 1}],
    }
    del data[missing_field]
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert missing_field in str(exc_info.value)


# ---------------------------------------------------------------------------
# format_version inválido
# ---------------------------------------------------------------------------

def test_unsupported_format_version(tmp_path: Path) -> None:
    data = {
        "format_version": 2,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [{"item_id": "a", "position": 1}],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert "format_version" in str(exc_info.value)


# ---------------------------------------------------------------------------
# items vazio ou inválido
# ---------------------------------------------------------------------------

def test_empty_items_list(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert "items" in str(exc_info.value)


def test_items_not_a_list(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": "not a list",
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError):
        load_ranking(f)


# ---------------------------------------------------------------------------
# item_id inválido ou ausente
# ---------------------------------------------------------------------------

def test_missing_item_id(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [{"position": 1}],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert "item_id" in str(exc_info.value)


def test_duplicate_item_id(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [
            {"item_id": "a", "position": 1},
            {"item_id": "a", "position": 2},
        ],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert "duplicado" in str(exc_info.value)


# ---------------------------------------------------------------------------
# position inválido
# ---------------------------------------------------------------------------

def test_missing_position(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [{"item_id": "a"}],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert "position" in str(exc_info.value)


def test_position_is_float(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [{"item_id": "a", "position": 1.5}],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert "position" in str(exc_info.value)


def test_position_is_zero(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [{"item_id": "a", "position": 0}],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert "position" in str(exc_info.value)


def test_position_is_negative(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [{"item_id": "a", "position": -1}],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError):
        load_ranking(f)


def test_position_is_string(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [{"item_id": "a", "position": "1"}],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError):
        load_ranking(f)


def test_duplicate_position(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [
            {"item_id": "a", "position": 1},
            {"item_id": "b", "position": 1},
        ],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert "duplicada" in str(exc_info.value)


def test_position_gap(tmp_path: Path) -> None:
    """Posições {1, 3} com n=2 não formam {1, 2}."""
    data = {
        "format_version": 1,
        "ranking_id": "r1",
        "name": "n",
        "origin": "o",
        "items": [
            {"item_id": "a", "position": 1},
            {"item_id": "b", "position": 3},
        ],
    }
    f = tmp_path / "r.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert "posições" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Erros de I/O e JSON
# ---------------------------------------------------------------------------

def test_file_not_found() -> None:
    with pytest.raises(RankLabError) as exc_info:
        load_ranking("nao_existe.json")
    assert "não encontrado" in str(exc_info.value)


def test_invalid_json(tmp_path: Path) -> None:
    f = tmp_path / "bad.json"
    f.write_text("{invalid json", encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_ranking(f)
    assert "JSON" in str(exc_info.value)


def test_json_not_object(tmp_path: Path) -> None:
    f = tmp_path / "arr.json"
    f.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(RankLabError):
        load_ranking(f)
