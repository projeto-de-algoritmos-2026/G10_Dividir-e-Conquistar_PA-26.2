"""Fixtures dos testes de navegador (extra opcional ``browser``)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from ranklab.server import create_server

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
AXE_PATH = Path(__file__).parent / "vendor" / "axe.min.js"


@pytest.fixture(scope="session")
def axe_source() -> str:
    if not AXE_PATH.is_file():
        pytest.fail(
            "axe.min.js ausente em tests/browser/vendor; veja docs/testes-navegador.md"
        )
    return AXE_PATH.read_text(encoding="utf-8")


def _generate_report(output: Path, examples: str) -> Path:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ranklab",
            "audit-report",
            f"{examples}/matriz.json",
            "--first-ranking",
            f"{examples}/ranking.json",
            "--second-ranking",
            f"{examples}/ranking-operacional.json",
            "--base-weights",
            f"{examples}/pesos.json",
            "--changed-weights",
            f"{examples}/pesos-alterados-muda.json",
            "--closest-criteria",
            "qualidade",
            "prazo_dias",
            "--selection-criterion",
            "qualidade",
            "--percentile",
            "50",
            "--output",
            str(output),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return output


@pytest.fixture(scope="session")
def report_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("report") / "relatorio.json"
    return _generate_report(output, "examples")


@pytest.fixture(scope="session")
def large_report_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("large") / "relatorio-large.json"
    return _generate_report(output, "examples/large")


@pytest.fixture(scope="session")
def invalid_report_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("invalid") / "invalido.json"
    path.write_text('{"format": "outro", "format_version": 2}\n', encoding="utf-8")
    return path


def _start_server(report: Path | None) -> Iterator[str]:
    server = create_server(report, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def server_with_report(report_path: Path) -> Iterator[str]:
    yield from _start_server(report_path)


@pytest.fixture
def server_with_large_report(large_report_path: Path) -> Iterator[str]:
    yield from _start_server(large_report_path)


@pytest.fixture
def server_without_report() -> Iterator[str]:
    yield from _start_server(None)


@pytest.fixture
def server_with_invalid_report(invalid_report_path: Path) -> Iterator[str]:
    yield from _start_server(invalid_report_path)


@pytest.fixture(scope="session")
def browser_type_launch_args() -> dict[str, object]:
    return {"headless": True}


@pytest.fixture(scope="session")
def playwright():
    pytest.importorskip("playwright")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright_instance:
        yield playwright_instance


@pytest.fixture(scope="session")
def browser(playwright, browser_type_launch_args: dict[str, object]):
    browser = playwright.chromium.launch(**browser_type_launch_args)
    try:
        yield browser
    finally:
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()


def run_axe(page, axe_source: str, *, context_selector: str | None = None) -> dict:
    """Injeta axe-core via evaluate (não depende de script-src da página)."""

    # A distribuição UMD do axe-core define `axe` no escopo global ao ser avaliada.
    page.evaluate(axe_source)
    options = {
        "runOnly": {
            "type": "tag",
            "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"],
        }
    }
    if context_selector:
        return page.evaluate(
            """async ({ selector, options }) => {
                const target = document.querySelector(selector);
                return await axe.run(target, options);
            }""",
            {"selector": context_selector, "options": options},
        )
    return page.evaluate(
        """async (options) => await axe.run(document, options)""",
        options,
    )


def assert_contrast_was_measured(results: dict) -> None:
    """Falha se o axe não mediu contraste, o que tornaria a ausência de violação vazia."""

    measured = {rule["id"] for rule in results.get("passes", [])}
    undecided = {rule["id"] for rule in results.get("incomplete", [])}
    assert "color-contrast" in measured
    assert "color-contrast" not in undecided


def serious_violations(results: dict) -> list[dict]:
    return [
        violation
        for violation in results.get("violations", [])
        if violation.get("impact") in {"critical", "serious"}
    ]


def assert_no_serious_violations(
    results: dict, *, allowed_ids: set[str] | None = None
) -> None:
    allowed_ids = allowed_ids or set()
    blocking = [
        violation
        for violation in serious_violations(results)
        if violation.get("id") not in allowed_ids
    ]
    if not blocking:
        return
    summary = json.dumps(
        [
            {
                "id": item["id"],
                "impact": item["impact"],
                "description": item["description"],
                "nodes": [node.get("target") for node in item.get("nodes", [])[:3]],
            }
            for item in blocking
        ],
        ensure_ascii=False,
        indent=2,
    )
    raise AssertionError(f"Violações críticas/sérias sem justificativa:\n{summary}")
