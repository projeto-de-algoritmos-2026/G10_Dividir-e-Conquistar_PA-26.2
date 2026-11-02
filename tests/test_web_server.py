"""Testes do comando serve e da leitura de relatórios pelo visualizador."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

import ranklab
from ranklab.io.errors import RankLabError
from ranklab.reporting import load_audit_report
from ranklab.server import STATIC_FILES, create_server

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


@pytest.fixture
def report_path(tmp_path: Path) -> Path:
    output = tmp_path / "relatorio.json"
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
    return output


def _start_server(report: Path | None) -> Iterator[str]:
    server = create_server(report, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def server_url(report_path: Path) -> Iterator[str]:
    yield from _start_server(report_path)


@pytest.fixture
def server_without_report() -> Iterator[str]:
    yield from _start_server(None)


def _get(url: str) -> tuple[int, dict[str, str], bytes]:
    try:
        with urllib.request.urlopen(url) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        with error:
            return error.code, dict(error.headers), error.read()


def test_load_audit_report_accepts_generated_report(report_path: Path) -> None:
    report = load_audit_report(report_path)

    assert report["format_version"] == 3


@pytest.mark.parametrize(
    ("content", "expected_message"),
    [
        ("{ inválido", "JSON inválido"),
        ("[]", "format"),
        ('{"format": "outro", "format_version": 3}', "format"),
        ('{"format": "ranklab-audit-report", "format_version": 2}', "versão suportada"),
        (
            '{"format": "ranklab-audit-report", "format_version": 3, "analyses": {}}',
            "seções ausentes: ordering_divergence",
        ),
    ],
)
def test_load_audit_report_rejects_invalid_content(
    tmp_path: Path, content: str, expected_message: str
) -> None:
    path = tmp_path / "relatorio.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(RankLabError, match=expected_message):
        load_audit_report(path)


def test_load_audit_report_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(RankLabError, match="arquivo não encontrado"):
        load_audit_report(tmp_path / "ausente.json")


@pytest.mark.parametrize("path", sorted(STATIC_FILES))
def test_server_delivers_interface_files_with_security_headers(
    server_url: str, path: str
) -> None:
    status, headers, body = _get(server_url + path)

    assert status == 200
    assert body
    assert headers["Content-Type"] == STATIC_FILES[path][1]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert "script-src 'self'" in headers["Content-Security-Policy"]


def test_every_interface_file_is_listed() -> None:
    interface_dir = Path(ranklab.__file__).parent / "web"
    listed = {filename for filename, _ in STATIC_FILES.values()}

    assert {path.name for path in interface_dir.iterdir()} == listed


def test_report_endpoint_returns_indicated_report(
    server_url: str, report_path: Path
) -> None:
    status, _, body = _get(f"{server_url}/api/report")

    assert status == 200
    assert json.loads(body) == json.loads(report_path.read_text(encoding="utf-8"))


def test_report_endpoint_is_not_found_without_report(server_without_report: str) -> None:
    status, _, body = _get(f"{server_without_report}/api/report")

    assert status == 404
    assert "--report" in json.loads(body)["error"]


def test_report_endpoint_reports_file_corrupted_after_start(
    server_url: str, report_path: Path
) -> None:
    report_path.write_text("{ inválido", encoding="utf-8")

    status, _, body = _get(f"{server_url}/api/report")

    assert status == 422
    assert "JSON inválido" in json.loads(body)["error"]


@pytest.mark.parametrize(
    "path",
    ["/web/app.js", "/reporting.py", "/..%2f..%2fpyproject.toml", "/index.html"],
)
def test_server_only_exposes_listed_files(server_url: str, path: str) -> None:
    status, _, _ = _get(server_url + path)

    assert status == 404


def test_serve_command_rejects_invalid_report(tmp_path: Path) -> None:
    path = tmp_path / "invalido.json"
    path.write_text("[]", encoding="utf-8")

    result = _run("serve", "--report", str(path), "--port", "0")

    assert result.returncode == 1
    assert result.stderr.startswith("Erro: ")


def test_serve_command_rejects_port_out_of_range() -> None:
    result = _run("serve", "--port", "70000")

    assert result.returncode == 2
    assert "porta deve estar" in result.stderr


def test_serve_command_starts_server_with_report(report_path: Path) -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "ranklab", "serve", "--report", str(report_path), "--port", "0"],
        cwd=REPOSITORY_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    try:
        assert process.stdout is not None
        banner = process.stdout.readline()
        url = banner.split()[2]

        status, _, body = _get(f"{url}api/report")

        assert status == 200
        assert json.loads(body)["format"] == "ranklab-audit-report"
    finally:
        process.terminate()
        process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()
