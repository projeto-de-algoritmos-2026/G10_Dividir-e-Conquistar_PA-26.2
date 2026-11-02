"""Fluxos principais do visualizador no navegador."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.browser


def test_valid_report_renders_sections(page, server_with_report: str) -> None:
    page.goto(server_with_report, wait_until="domcontentloaded")
    page.locator("#divergencia").wait_for()
    assert page.get_by_role("navigation", name="Análises do relatório").is_visible()
    assert page.get_by_role("link", name="Divergência de ordenação").is_visible()
    assert page.locator("#content").get_by_text("fornecedor-a").count() > 0
    assert page.get_by_role("link", name="Ir para o conteúdo").count() == 1


def test_invalid_report_shows_error_state(
    page, server_with_invalid_report: str
) -> None:
    page.goto(server_with_invalid_report, wait_until="domcontentloaded")
    page.get_by_role("heading", name="Não foi possível carregar o relatório").wait_for()
    assert page.locator("#content").get_by_role("alert").count() >= 1
    assert page.get_by_role("navigation", name="Análises do relatório").is_hidden()


def test_absence_of_report_shows_empty_state(page, server_without_report: str) -> None:
    page.goto(server_without_report, wait_until="domcontentloaded")
    page.get_by_role("heading", name="Abra um relatório para começar").wait_for()
    assert (
        page.locator("#content")
        .get_by_text("Escolha um JSON gerado pelo RankLab")
        .count()
        == 1
    )


def test_file_swap_replaces_report(
    page, server_without_report: str, report_path: Path, invalid_report_path: Path
) -> None:
    page.goto(server_without_report, wait_until="domcontentloaded")
    page.get_by_role("heading", name="Abra um relatório para começar").wait_for()

    page.set_input_files("#report-file", str(report_path))
    page.locator("#divergencia").wait_for()
    assert page.locator("#content").get_by_text("fornecedor-a").count() > 0

    page.set_input_files("#report-file", str(invalid_report_path))
    page.get_by_role("heading", name="Não foi possível exibir o relatório").wait_for()
    assert page.get_by_role("navigation", name="Análises do relatório").is_hidden()
    assert page.locator("#content").get_by_text("fornecedor-a").count() == 0

    page.set_input_files("#report-file", str(report_path))
    page.locator("#divergencia").wait_for()
    assert page.locator("#content").get_by_text("fornecedor-a").count() > 0


def test_large_report_declares_synthetic_data(
    page, server_with_large_report: str
) -> None:
    page.goto(server_with_large_report, wait_until="domcontentloaded")
    page.locator("#divergencia").wait_for()
    content = page.locator("#content")
    assert content.get_by_text("fornecedor-32").count() > 0
    assert "não sustentam decisões reais" in content.inner_text()


def test_keyboard_skip_link_reaches_main(page, server_with_report: str) -> None:
    page.goto(server_with_report, wait_until="domcontentloaded")
    page.locator("#divergencia").wait_for()
    page.locator("body").focus()
    page.keyboard.press("Tab")
    focused = page.evaluate(
        "() => document.activeElement && document.activeElement.className"
    )
    assert "skip-link" in focused
    page.keyboard.press("Enter")
    assert (
        page.evaluate("() => document.activeElement && document.activeElement.id")
        == "content"
    )


def test_keyboard_reaches_primary_controls(page, server_with_report: str) -> None:
    page.goto(server_with_report, wait_until="domcontentloaded")
    page.locator("#divergencia").wait_for()
    reached: set[str] = set()
    for _ in range(20):
        page.keyboard.press("Tab")
        reached.add(page.evaluate("() => document.activeElement.id"))
    assert {"report-file", "load-example", "matrix-file", "generate-report"} <= reached


def test_mobile_width_keeps_primary_controls(browser, server_with_report: str) -> None:
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        is_mobile=True,
    )
    mobile = context.new_page()
    try:
        mobile.goto(server_with_report, wait_until="domcontentloaded")
        mobile.locator("#divergencia").wait_for()
        assert mobile.get_by_text("Abrir relatório", exact=True).is_visible()
        assert mobile.locator("#load-example").is_visible()
        assert mobile.locator("#generate-report").is_visible()
        # Tabelas largas rolam no próprio contêiner; a página não pode transbordar.
        assert mobile.evaluate(
            "() => document.documentElement.scrollWidth <= window.innerWidth"
        )
    finally:
        context.close()
