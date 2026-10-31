"""Testes de integração do comando ``compare-weights``."""

from __future__ import annotations

from pathlib import Path

from ranklab.cli import main


def _run(
    monkeypatch,
    changed_weights: str | Path,
) -> int:
    monkeypatch.setattr(
        "sys.argv",
        [
            "ranklab",
            "compare-weights",
            "examples/matriz.json",
            "--base-weights",
            "examples/pesos.json",
            "--changed-weights",
            str(changed_weights),
        ],
    )
    return main()


def test_compare_weights_cli_reports_changed_order_side_by_side(
    monkeypatch,
    capsys,
) -> None:
    assert _run(monkeypatch, "examples/pesos-alterados-muda.json") == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    captured.out.encode("cp1252")
    assert "Comparação de pesos da matriz 'fornecedores-2026-matriz'" in captured.out
    assert "normalização: min-max orientada pela direção" in captured.out
    assert "desempate: score decrescente; item_id lexicográfico crescente" in captured.out
    assert "qualidade=higher_is_better" in captured.out
    assert "prazo_dias=lower_is_better" in captured.out
    assert "Cenário base — pesos" in captured.out
    assert "qualidade: 2.000000 -> 0.666667" in captured.out
    assert "Cenário alterado — pesos" in captured.out
    assert "prazo_dias: 3.000000 -> 0.750000" in captured.out
    assert (
        "fornecedor-a | 1 | 2 | -1 | 0.833333 | 0.625000 | "
        "-0.208333 | fornecedor-b"
    ) in captured.out
    assert (
        "fornecedor-b | 2 | 1 | +1 | 0.333333 | 0.750000 | "
        "+0.416667 | fornecedor-a"
    ) in captured.out
    assert "Inversões: 1 de 3" in captured.out
    assert "Distância de Kendall normalizada: 0.333333" in captured.out


def test_compare_weights_cli_reports_changed_scores_with_stable_order(
    monkeypatch,
    capsys,
) -> None:
    assert _run(monkeypatch, "examples/pesos-alterados-estavel.json") == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "fornecedor-a | 1 | 1 | +0 | 0.833333 | 0.800000" in captured.out
    assert "fornecedor-b | 2 | 2 | +0 | 0.333333 | 0.400000" in captured.out
    assert "fornecedor-c | 3 | 3 | +0 | 0.296296 | 0.266667" in captured.out
    assert "Inversões: 0 de 3" in captured.out
    assert "Distância de Kendall normalizada: 0.000000" in captured.out


def test_compare_weights_cli_reports_missing_changed_weights(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    missing = tmp_path / "pesos-ausentes.json"

    assert _run(monkeypatch, missing) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(missing) in captured.err
    assert "arquivo não encontrado" in captured.err
