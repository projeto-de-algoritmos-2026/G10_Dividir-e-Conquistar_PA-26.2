"""Testes ponta a ponta dos comandos documentados para a demonstração."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ranklab.io.readers import load_matrix

REPOSITORY_ROOT = Path(__file__).parent.parent


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ranklab", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )


@pytest.mark.parametrize(
    ("arguments", "expected_output"),
    [
        (("load-matrix", "examples/matriz.json"), "Matriz carregada"),
        (("load-ranking", "examples/ranking.json"), "Ranking carregado"),
        (
            (
                "compare-rankings",
                "examples/ranking.json",
                "examples/ranking-operacional.json",
            ),
            "Quantidade de pares discordantes: 1 de 3",
        ),
        (
            ("select", "examples/valores-qualidade.json", "--percentile", "50"),
            "k=2): 90",
        ),
        (
            (
                "closest-pair",
                "examples/matriz.json",
                "qualidade",
                "prazo_dias",
            ),
            "'fornecedor-a' e 'fornecedor-c'",
        ),
        (
            (
                "compare-weights",
                "examples/matriz.json",
                "--base-weights",
                "examples/pesos.json",
                "--changed-weights",
                "examples/pesos-alterados-muda.json",
            ),
            "fornecedor-b | 2 | 1 | +1",
        ),
    ],
)
def test_documented_demo_commands(
    arguments: tuple[str, ...],
    expected_output: str,
) -> None:
    result = _run(*arguments)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert expected_output in result.stdout


def test_quality_values_example_is_derived_from_matrix() -> None:
    matrix = load_matrix(REPOSITORY_ROOT / "examples" / "matriz.json")
    values = json.loads(
        (REPOSITORY_ROOT / "examples" / "valores-qualidade.json").read_text(
            encoding="utf-8"
        )
    )

    assert values == [item.values["qualidade"] for item in matrix.items]


def test_integrated_audit_report_uses_all_demo_inputs(tmp_path: Path) -> None:
    output = tmp_path / "relatorio-demonstracao.json"
    result = _run(
        "audit-report",
        "examples/matriz.json",
        "--first-ranking",
        "examples/ranking.json",
        "--second-ranking",
        "examples/ranking-operacional.json",
        "--base-weights",
        "examples/pesos.json",
        "--changed-weights",
        "examples/pesos-alterados-muda.json",
        "--closest-criteria",
        "qualidade",
        "prazo_dias",
        "--selection-criterion",
        "qualidade",
        "--percentile",
        "50",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert "Relatório auditável escrito" in result.stdout
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["format"] == "ranklab-audit-report"
    assert report["format_version"] == 2
    analyses = report["analyses"]
    assert set(analyses) == {
        "ordering_divergence",
        "proximity",
        "order_selection",
        "weight_sensitivity",
    }
    assert analyses["ordering_divergence"]["discordant_pair_count"] == 1
    assert analyses["ordering_divergence"]["kendall_normalized_distance"] == pytest.approx(
        1 / 3
    )
    assert analyses["proximity"]["item_ids"] == ["fornecedor-a", "fornecedor-c"]
    assert analyses["proximity"]["distance"] == pytest.approx(0.7474235582)
    assert analyses["order_selection"]["value"] == 90.0
    assert analyses["order_selection"]["source"]["criterion_id"] == "qualidade"
    assert analyses["weight_sensitivity"]["ranking_divergence"][
        "discordant_pair_count"
    ] == 1


def test_audit_report_rejects_conflicting_selection_sources() -> None:
    result = _run(
        "audit-report",
        "examples/matriz.json",
        "--first-ranking",
        "examples/ranking.json",
        "--second-ranking",
        "examples/ranking-operacional.json",
        "--base-weights",
        "examples/pesos.json",
        "--changed-weights",
        "examples/pesos-alterados-muda.json",
        "--closest-criteria",
        "qualidade",
        "prazo_dias",
        "--selection-values",
        "examples/valores-qualidade.json",
        "--selection-criterion",
        "qualidade",
        "--k",
        "2",
    )

    assert result.returncode == 2
    assert "not allowed with argument" in result.stderr
