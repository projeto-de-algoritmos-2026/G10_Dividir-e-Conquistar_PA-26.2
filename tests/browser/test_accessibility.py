"""Auditoria automatizada de acessibilidade nos estados principais."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.browser.conftest import (
    assert_contrast_was_measured,
    assert_no_serious_violations,
    run_axe,
    serious_violations,
)

pytestmark = pytest.mark.browser

# Violações com justificativa registrada em docs/testes-navegador.md.
ALLOWED_SERIOUS_IDS: set[str] = set()


@pytest.mark.parametrize("color_scheme", ["light", "dark"])
def test_axe_on_valid_report(
    page,
    server_with_report: str,
    axe_source: str,
    color_scheme: str,
) -> None:
    page.emulate_media(color_scheme=color_scheme)
    page.goto(server_with_report, wait_until="domcontentloaded")
    page.locator("#divergencia").wait_for()
    results = run_axe(page, axe_source)
    assert_no_serious_violations(results, allowed_ids=ALLOWED_SERIOUS_IDS)
    assert_contrast_was_measured(results)


@pytest.mark.parametrize("color_scheme", ["light", "dark"])
def test_axe_on_empty_state(
    page,
    server_without_report: str,
    axe_source: str,
    color_scheme: str,
) -> None:
    page.emulate_media(color_scheme=color_scheme)
    page.goto(server_without_report, wait_until="domcontentloaded")
    page.get_by_role("heading", name="Abra um relatório para começar").wait_for()
    results = run_axe(page, axe_source)
    assert_no_serious_violations(results, allowed_ids=ALLOWED_SERIOUS_IDS)
    assert_contrast_was_measured(results)


@pytest.mark.parametrize("color_scheme", ["light", "dark"])
def test_axe_on_invalid_report(
    page,
    server_with_invalid_report: str,
    axe_source: str,
    color_scheme: str,
) -> None:
    page.emulate_media(color_scheme=color_scheme)
    page.goto(server_with_invalid_report, wait_until="domcontentloaded")
    page.get_by_role("heading", name="Não foi possível carregar o relatório").wait_for()
    results = run_axe(page, axe_source)
    assert_no_serious_violations(results, allowed_ids=ALLOWED_SERIOUS_IDS)
    assert_contrast_was_measured(results)


def test_axe_after_file_swap(
    page,
    server_without_report: str,
    report_path: Path,
    axe_source: str,
) -> None:
    page.goto(server_without_report, wait_until="domcontentloaded")
    page.set_input_files("#report-file", str(report_path))
    page.locator("#divergencia").wait_for()
    results = run_axe(page, axe_source)
    assert_no_serious_violations(results, allowed_ids=ALLOWED_SERIOUS_IDS)


def test_axe_detects_low_contrast(
    page,
    server_without_report: str,
    axe_source: str,
) -> None:
    # Controle negativo: garante que a auditoria reprova texto ilegível. O estilo
    # vai por CSSOM porque a CSP da página bloqueia o atributo style.
    page.goto(server_without_report, wait_until="domcontentloaded")
    page.get_by_role("heading", name="Abra um relatório para começar").wait_for()
    page.evaluate(
        """() => {
            const paragraph = document.createElement("p");
            paragraph.textContent = "baixo contraste";
            paragraph.style.color = "#777777";
            paragraph.style.background = "#808080";
            document.querySelector("#content").prepend(paragraph);
        }"""
    )
    results = run_axe(page, axe_source)
    assert "color-contrast" in {item["id"] for item in serious_violations(results)}
