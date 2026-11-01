from __future__ import annotations

import json
from pathlib import Path

from ranklab.cli import main


def test_select_cli_reports_order(tmp_path: Path, monkeypatch, capsys) -> None:
    path = tmp_path / "values.json"
    path.write_text(json.dumps([8, 2, 5, 1]), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["ranklab", "select", str(path), "--k", "2"])

    assert main() == 0
    output = capsys.readouterr().out
    assert "k=2" in output
    assert "2" in output


def test_select_cli_reports_missing_file_consistently(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    missing = tmp_path / "valores-ausentes.json"
    monkeypatch.setattr(
        "sys.argv",
        ["ranklab", "select", str(missing), "--k", "1"],
    )

    assert main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(missing) in captured.err
    assert "arquivo não encontrado" in captured.err


def test_closest_pair_cli_reports_numeric_proximity(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "ranklab",
            "closest-pair",
            "examples/matriz.json",
            "qualidade",
            "prazo_dias",
        ],
    )

    assert main() == 0
    output = capsys.readouterr().out
    assert "Par mais próximo" in output
    assert "distância Euclidiana normalizada" in output
