from __future__ import annotations

import json
from pathlib import Path

from ranklab.cli import main


def _run(
    monkeypatch,
    matrix_path: str | Path,
    weights_path: str | Path,
) -> int:
    monkeypatch.setattr(
        "sys.argv",
        [
            "ranklab",
            "aggregate-ranking",
            str(matrix_path),
            "--weights",
            str(weights_path),
        ],
    )
    return main()


def test_aggregate_ranking_cli_shows_auditable_result(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    weights_path = tmp_path / "pesos.json"
    weights_path.write_text(
        json.dumps({"qualidade": 2, "prazo_dias": 1}),
        encoding="utf-8",
    )

    assert _run(monkeypatch, "examples/matriz.json", weights_path) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "qualidade: 2.000000 -> 0.666667" in captured.out
    assert "prazo_dias: 1.000000 -> 0.333333" in captured.out
    assert "posição | item_id | qualidade | prazo_dias | score" in captured.out
    assert "1 | fornecedor-a | 1.000000 | 0.500000 | 0.833333" in captured.out
    assert "2 | fornecedor-b | 0.000000 | 1.000000 | 0.333333" in captured.out
    assert "3 | fornecedor-c | 0.444444 | 0.000000 | 0.296296" in captured.out
    assert "arredondados apenas para exibição" in captured.out


def test_aggregate_ranking_cli_rejects_malformed_weights_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    weights_path = tmp_path / "pesos.json"
    weights_path.write_text("{não é JSON", encoding="utf-8")

    assert _run(monkeypatch, "examples/matriz.json", weights_path) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(weights_path) in captured.err
    assert "JSON inválido" in captured.err
    assert "linha" in captured.err


def test_aggregate_ranking_cli_requires_json_object(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    weights_path = tmp_path / "pesos.json"
    weights_path.write_text("[]", encoding="utf-8")

    assert _run(monkeypatch, "examples/matriz.json", weights_path) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "deve conter um objeto JSON" in captured.err


def test_aggregate_ranking_cli_reports_semantically_invalid_weights(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    weights_path = tmp_path / "pesos.json"
    weights_path.write_text(
        json.dumps({"qualidade": -1, "prazo_dias": 1}),
        encoding="utf-8",
    )

    assert _run(monkeypatch, "examples/matriz.json", weights_path) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Erro:" in captured.err
    assert "qualidade" in captured.err


def test_aggregate_ranking_cli_reports_missing_weights_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    missing = tmp_path / "ausente.json"

    assert _run(monkeypatch, "examples/matriz.json", missing) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(missing) in captured.err
    assert "arquivo não encontrado" in captured.err


def test_aggregate_ranking_cli_rejects_non_utf8_weights_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    weights_path = tmp_path / "pesos.json"
    weights_path.write_bytes(b'{"qualidade": "\xff"}')

    assert _run(monkeypatch, "examples/matriz.json", weights_path) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(weights_path) in captured.err
    assert "UTF-8 válido" in captured.err
