from __future__ import annotations

import json
from pathlib import Path

from ranklab.cli import main


def _write_ranking(path: Path, ranking_id: str, ordered_ids: list[str]) -> Path:
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "ranking_id": ranking_id,
                "name": ranking_id,
                "origin": f"arquivo-{ranking_id}",
                "items": [
                    {"item_id": item_id, "position": position}
                    for position, item_id in enumerate(ordered_ids, start=1)
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_audit_report_contains_distinct_reproducible_sections(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    first = _write_ranking(tmp_path / "first.json", "first", [
        "fornecedor-a", "fornecedor-b", "fornecedor-c"
    ])
    second = _write_ranking(tmp_path / "second.json", "second", [
        "fornecedor-b", "fornecedor-a", "fornecedor-c"
    ])
    values = tmp_path / "values.json"
    values.write_text("[9, 2, 7, 4]", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "ranklab",
            "audit-report",
            "examples/matriz.json",
            "--first-ranking",
            str(first),
            "--second-ranking",
            str(second),
            "--base-weights",
            "examples/pesos.json",
            "--changed-weights",
            "examples/pesos-alterados-muda.json",
            "--closest-criteria",
            "qualidade",
            "prazo_dias",
            "--selection-values",
            str(values),
            "--k",
            "2",
        ],
    )

    assert main() == 0
    captured = capsys.readouterr()
    report = json.loads(captured.out)

    assert captured.err == ""
    assert report["format"] == "ranklab-audit-report"
    analyses = report["analyses"]
    assert set(analyses) == {
        "ordering_divergence",
        "proximity",
        "median_position",
        "weight_sensitivity",
    }
    assert analyses["ordering_divergence"]["discordant_pair_count"] == 1
    assert analyses["ordering_divergence"]["positions"][0]["position_delta"] == -1
    assert analyses["proximity"]["metric"] == "Euclidiana"
    assert "não representa similaridade geral" in analyses["proximity"]["interpretation"]
    assert analyses["proximity"]["source_values"]["fornecedor-a"]["qualidade"] == 92.5
    assert analyses["median_position"]["order"] == 2
    assert analyses["median_position"]["value"] == 4
    assert analyses["weight_sensitivity"]["base"]["weights"][0]["input"] == 2.0
    assert analyses["weight_sensitivity"]["ranking_divergence"]["discordant_pair_count"] == 1


def test_audit_report_writes_file_and_reports_write_errors(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    first = _write_ranking(tmp_path / "first.json", "first", ["fornecedor-a", "fornecedor-b", "fornecedor-c"])
    second = _write_ranking(tmp_path / "second.json", "second", ["fornecedor-a", "fornecedor-b", "fornecedor-c"])
    values = tmp_path / "values.json"
    values.write_text("[1, 2, 3]", encoding="utf-8")
    output = tmp_path / "report.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ranklab", "audit-report", "examples/matriz.json",
            "--first-ranking", str(first), "--second-ranking", str(second),
            "--base-weights", "examples/pesos.json",
            "--changed-weights", "examples/pesos-alterados-estavel.json",
            "--closest-criteria", "qualidade", "prazo_dias",
            "--selection-values", str(values), "--percentile", "50",
            "--output", str(output),
        ],
    )

    assert main() == 0
    captured = capsys.readouterr()
    assert captured.out == f"Relatório auditável escrito em {output}\n"
    assert json.loads(output.read_text(encoding="utf-8"))["analyses"]["median_position"]["percentile"] == 50
