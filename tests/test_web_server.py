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

from ranklab.io.errors import RankLabError
from ranklab.reporting import load_audit_report
from ranklab.server import STATIC_FILES, create_server
from ranklab.server import MAX_REQUEST_BYTES

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


def _post(url: str, body: bytes) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        with error:
            return error.code, dict(error.headers), error.read()


def _api_payload() -> dict[str, object]:
    def document(relative_path: str) -> dict[str, str]:
        return {
            "source": str(Path(relative_path)),
            "content": (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8"),
        }

    return {
        "inputs": {
            "matrix": document("examples/matriz.json"),
            "first_ranking": document("examples/ranking.json"),
            "second_ranking": document("examples/ranking-operacional.json"),
            "base_weights": document("examples/pesos.json"),
            "changed_weights": document("examples/pesos-alterados-muda.json"),
        },
        "parameters": {
            "closest_criteria": ["qualidade", "prazo_dias"],
            "selection": {
                "source": {
                    "type": "matrix_criterion",
                    "criterion_id": "qualidade",
                },
                "percentile": 50,
            },
        },
    }


def test_load_audit_report_accepts_generated_report(report_path: Path) -> None:
    report = load_audit_report(report_path)

    assert report["format_version"] == 2


@pytest.mark.parametrize(
    ("content", "expected_message"),
    [
        ("{ inválido", "JSON inválido"),
        ("[]", "format"),
        ('{"format": "outro", "format_version": 2}', "format"),
        ('{"format": "ranklab-audit-report", "format_version": 1}', "versão suportada"),
        (
            '{"format": "ranklab-audit-report", "format_version": 2, "analyses": {}}',
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


def test_report_endpoint_returns_indicated_report(
    server_url: str, report_path: Path
) -> None:
    status, _, body = _get(f"{server_url}/api/report")

    assert status == 200
    assert json.loads(body) == json.loads(report_path.read_text(encoding="utf-8"))


def test_post_report_matches_cli_report(
    server_url: str, report_path: Path
) -> None:
    body = json.dumps(_api_payload(), ensure_ascii=False).encode("utf-8")

    status, _, response_body = _post(f"{server_url}/api/report", body)

    assert status == 200
    assert json.loads(response_body) == json.loads(
        report_path.read_text(encoding="utf-8")
    )


def test_post_report_maps_document_validation_error(server_url: str) -> None:
    payload = _api_payload()
    payload["inputs"]["matrix"]["content"] = "{ inválido"  # type: ignore[index]

    status, _, body = _post(
        f"{server_url}/api/report",
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )
    error = json.loads(body)["error"]

    assert status == 422
    assert error["code"] == "validation_error"
    assert error["input"] == "matrix"
    assert "JSON inválido" in error["message"]
    assert "Traceback" not in body.decode("utf-8")


def test_post_report_preserves_validation_field_path(server_url: str) -> None:
    payload = _api_payload()
    matrix_document = payload["inputs"]["matrix"]  # type: ignore[index]
    matrix = json.loads(matrix_document["content"])
    del matrix["items"][0]["values"]["qualidade"]
    matrix_document["content"] = json.dumps(matrix)

    status, _, body = _post(
        f"{server_url}/api/report",
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )
    error = json.loads(body)["error"]

    assert status == 422
    assert error["input"] == "matrix"
    assert error["field_path"] == "items[0].values.qualidade"
    assert error["message"].endswith("items[0].values.qualidade: valor ausente")


def test_post_report_accepts_external_selection_list(server_url: str) -> None:
    payload = _api_payload()
    payload["inputs"]["selection_values"] = {  # type: ignore[index]
        "source": "valores.json",
        "content": "[4, 2, 4, 1]",
    }
    payload["parameters"]["selection"] = {  # type: ignore[index]
        "source": {"type": "json_list"},
        "k": 3,
    }

    status, _, body = _post(
        f"{server_url}/api/report",
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )
    selection = json.loads(body)["analyses"]["order_selection"]

    assert status == 200
    assert selection["value"] == 4
    assert selection["display"]["ordered_values"] == [1, 2, 4, 4]


def test_post_report_rejects_request_above_limit(server_url: str) -> None:
    body = b"{}" + b" " * (MAX_REQUEST_BYTES - 1)

    status, _, response_body = _post(f"{server_url}/api/report", body)

    assert len(body) == MAX_REQUEST_BYTES + 1
    assert status == 413
    assert json.loads(response_body)["error"]["code"] == "request_too_large"


def test_post_report_reads_request_at_limit(server_url: str) -> None:
    body = b"{}" + b" " * (MAX_REQUEST_BYTES - 2)

    status, _, response_body = _post(f"{server_url}/api/report", body)

    assert len(body) == MAX_REQUEST_BYTES
    assert status == 400
    assert json.loads(response_body)["error"]["code"] == "invalid_request"


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
