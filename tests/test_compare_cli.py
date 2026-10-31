"""Testes de integração do comando ``compare-rankings``."""

from __future__ import annotations

import json
from pathlib import Path

from ranklab.cli import main


def _write_ranking(path: Path, ranking_id: str, ordered_ids: list[str]) -> Path:
    data = {
        "format_version": 1,
        "ranking_id": ranking_id,
        "name": ranking_id,
        "origin": "teste",
        "items": [
            {"item_id": item_id, "position": position}
            for position, item_id in enumerate(ordered_ids, start=1)
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_compare_rankings_command_prints_result_and_pairs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    first = _write_ranking(tmp_path / "first.json", "first", ["a", "b", "c"])
    second = _write_ranking(tmp_path / "second.json", "second", ["c", "a", "b"])
    monkeypatch.setattr(
        "sys.argv",
        ["ranklab", "compare-rankings", str(first), str(second)],
    )

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Quantidade de pares discordantes: 2 de 3" in captured.out
    assert "Distância de Kendall normalizada: 0.666667" in captured.out
    assert "'a' antes de 'c' no primeiro" in captured.out
    assert "'b' antes de 'c' no primeiro" in captured.out
    assert captured.err == ""


def test_compare_rankings_command_reports_incompatible_sets(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    first = _write_ranking(tmp_path / "first.json", "first", ["a", "b"])
    second = _write_ranking(tmp_path / "second.json", "second", ["a", "c"])
    monkeypatch.setattr(
        "sys.argv",
        ["ranklab", "compare-rankings", str(first), str(second)],
    )

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "apenas no primeiro" in captured.err
    assert "apenas no segundo" in captured.err


def test_compare_rankings_command_rejects_invalid_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    first = _write_ranking(tmp_path / "first.json", "first", ["a", "b"])
    second = _write_ranking(tmp_path / "second.json", "second", ["a", "b"])
    invalid_data = json.loads(second.read_text(encoding="utf-8"))
    invalid_data["items"][1]["position"] = 1
    second.write_text(json.dumps(invalid_data), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        ["ranklab", "compare-rankings", str(first), str(second)],
    )

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "posição duplicada" in captured.err


def test_compare_rankings_command_reports_missing_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    missing = tmp_path / "missing.json"
    second = _write_ranking(tmp_path / "second.json", "second", ["a", "b"])
    monkeypatch.setattr(
        "sys.argv",
        ["ranklab", "compare-rankings", str(missing), str(second)],
    )

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "arquivo não encontrado" in captured.err


def test_compare_rankings_command_omits_large_pair_list(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    item_ids = [f"item-{index:03d}" for index in range(101)]
    first = _write_ranking(tmp_path / "first.json", "first", item_ids)
    second = _write_ranking(
        tmp_path / "second.json",
        "second",
        list(reversed(item_ids)),
    )
    monkeypatch.setattr(
        "sys.argv",
        ["ranklab", "compare-rankings", str(first), str(second)],
    )

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Quantidade de pares discordantes: 5050 de 5050" in captured.out
    assert "Pares explicativos omitidos" in captured.out
    assert "limite é 100 itens" in captured.out
    assert captured.err == ""
