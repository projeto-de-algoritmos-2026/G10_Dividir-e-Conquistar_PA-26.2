"""Testes para o leitor de matriz de pontuação."""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from ranklab.domain.models import ScoringMatrix
from ranklab.io.errors import RankLabError
from ranklab.io.readers import load_matrix

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_load_example_matrix() -> None:
    m = load_matrix(EXAMPLES_DIR / "matriz.json")
    assert isinstance(m, ScoringMatrix)
    assert m.matrix_id == "fornecedores-2026-matriz"
    assert len(m.criteria) == 2
    assert len(m.items) == 3


def test_example_matrix_values() -> None:
    m = load_matrix(EXAMPLES_DIR / "matriz.json")
    item_a = next(it for it in m.items if it.item_id == "fornecedor-a")
    assert item_a.values["qualidade"] == pytest.approx(92.5)
    assert item_a.values["prazo_dias"] == pytest.approx(12.0)


def test_negative_and_zero_values_allowed(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"},
        ],
        "items": [
            {"item_id": "a", "values": {"c1": -5.0}},
            {"item_id": "b", "values": {"c1": 0}},
        ],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    m = load_matrix(f)
    assert m.items[0].values["c1"] == pytest.approx(-5.0)
    assert m.items[1].values["c1"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Campos obrigatórios no topo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("missing_field", [
    "format_version", "matrix_id", "name", "origin", "criteria", "items",
])
def test_missing_top_level_field(tmp_path: Path, missing_field: str) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"},
        ],
        "items": [{"item_id": "a", "values": {"c1": 1.0}}],
    }
    del data[missing_field]
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert missing_field in str(exc_info.value)


# ---------------------------------------------------------------------------
# Critérios inválidos
# ---------------------------------------------------------------------------

def test_empty_criteria(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [],
        "items": [{"item_id": "a", "values": {}}],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert "criteria" in str(exc_info.value)


@pytest.mark.parametrize("missing_field", ["criterion_id", "name", "direction", "unit"])
def test_missing_criterion_field(tmp_path: Path, missing_field: str) -> None:
    crit = {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"}
    del crit[missing_field]
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [crit],
        "items": [{"item_id": "a", "values": {}}],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert missing_field in str(exc_info.value)


def test_invalid_direction(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "sideways", "unit": "pts"},
        ],
        "items": [{"item_id": "a", "values": {"c1": 1.0}}],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert "direction" in str(exc_info.value)


def test_duplicate_criterion_id(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"},
            {"criterion_id": "c1", "name": "C1b", "direction": "lower_is_better", "unit": "pts"},
        ],
        "items": [{"item_id": "a", "values": {"c1": 1.0}}],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert "duplicado" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Items inválidos
# ---------------------------------------------------------------------------

def test_empty_items(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"},
        ],
        "items": [],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert "items" in str(exc_info.value)


def test_duplicate_item_id(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"},
        ],
        "items": [
            {"item_id": "a", "values": {"c1": 1.0}},
            {"item_id": "a", "values": {"c1": 2.0}},
        ],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert "duplicado" in str(exc_info.value)


def test_missing_criterion_value_in_item(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"},
            {"criterion_id": "c2", "name": "C2", "direction": "lower_is_better", "unit": "ms"},
        ],
        "items": [
            {"item_id": "a", "values": {"c1": 1.0}},  # c2 ausente
        ],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert "c2" in str(exc_info.value)


def test_extra_criterion_value_in_item(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"},
        ],
        "items": [
            {"item_id": "a", "values": {"c1": 1.0, "c_extra": 99}},
        ],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert "c_extra" in str(exc_info.value)


def test_null_value_rejected(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"},
        ],
        "items": [{"item_id": "a", "values": {"c1": None}}],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert "c1" in str(exc_info.value)


def test_boolean_value_rejected(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"},
        ],
        "items": [{"item_id": "a", "values": {"c1": True}}],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert "c1" in str(exc_info.value)


def test_string_value_rejected(tmp_path: Path) -> None:
    data = {
        "format_version": 1,
        "matrix_id": "m1",
        "name": "n",
        "origin": "o",
        "criteria": [
            {"criterion_id": "c1", "name": "C1", "direction": "higher_is_better", "unit": "pts"},
        ],
        "items": [{"item_id": "a", "values": {"c1": "10"}}],
    }
    f = tmp_path / "m.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RankLabError) as exc_info:
        load_matrix(f)
    assert "c1" in str(exc_info.value)
