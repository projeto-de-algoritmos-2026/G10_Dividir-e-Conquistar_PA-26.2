"""Servidor local do visualizador web, somente com a biblioteca padrão."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ranklab.io.errors import RankLabError
from ranklab.reporting import load_audit_report

# Lista fechada: nenhum caminho da URL chega ao sistema de arquivos.
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/report.js": ("report.js", "text/javascript; charset=utf-8"),
    "/dom.js": ("dom.js", "text/javascript; charset=utf-8"),
    "/charts.js": ("charts.js", "text/javascript; charset=utf-8"),
    "/chart-views.js": ("chart-views.js", "text/javascript; charset=utf-8"),
}

CONTENT_SECURITY_POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


def _build_handler(report_path: Path | None) -> type[BaseHTTPRequestHandler]:
    class ViewerHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - nome exigido por BaseHTTPRequestHandler
            path = urlsplit(self.path).path
            if path == "/api/report":
                self._send_report()
            elif path in STATIC_FILES:
                filename, content_type = STATIC_FILES[path]
                body = files("ranklab").joinpath("web", filename).read_bytes()
                self._send(HTTPStatus.OK, content_type, body)
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "recurso não encontrado"})

        def _send_report(self) -> None:
            if report_path is None:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "o servidor foi iniciado sem --report"},
                )
                return
            # Lê a cada requisição: regenerar o relatório não exige reiniciar o servidor.
            try:
                report = load_audit_report(report_path)
            except RankLabError as exc:
                self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(exc)})
                return
            self._send_json(HTTPStatus.OK, report)

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(status, "application/json; charset=utf-8", body)

        def _send(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
            self.end_headers()
            self.wfile.write(body)

    return ViewerHandler


def create_server(
    report_path: Path | None,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> ThreadingHTTPServer:
    """Cria o servidor sem iniciá-lo; ``port=0`` escolhe uma porta livre."""

    return ThreadingHTTPServer((host, port), _build_handler(report_path))
