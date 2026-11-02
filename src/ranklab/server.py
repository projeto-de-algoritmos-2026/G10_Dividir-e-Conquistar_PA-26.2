"""Servidor local do visualizador web, somente com a biblioteca padrão."""

from __future__ import annotations

import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ranklab.io.errors import RankLabError
from ranklab.algorithms import (
    ClosestPairError,
    RankingComparisonError,
    SelectionError,
    WeightedRankingError,
)
from ranklab.io.analysis_inputs import parse_selection_values, parse_weights
from ranklab.io.readers import parse_matrix, parse_ranking
from ranklab.reporting import load_audit_report
from ranklab.services import (
    AuditReportRequest,
    WeightSensitivityRequest,
    generate_audit_report,
    generate_weight_sensitivity,
)

# Lista fechada: nenhum caminho da URL chega ao sistema de arquivos.
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/report.js": ("report.js", "text/javascript; charset=utf-8"),
    "/form.js": ("form.js", "text/javascript; charset=utf-8"),
}

CONTENT_SECURITY_POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
MAX_REQUEST_BYTES = 1_048_576
MAX_DISCARDED_BYTES = 16 * MAX_REQUEST_BYTES
DISCARD_TIMEOUT_SECONDS = 5.0
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_INPUTS = {
    "matrix": "matriz.json",
    "first_ranking": "ranking.json",
    "second_ranking": "ranking-operacional.json",
    "base_weights": "pesos.json",
    "changed_weights": "pesos-alterados-muda.json",
}


@dataclass(frozen=True)
class _ApiError(Exception):
    status: HTTPStatus
    code: str
    message: str
    input_name: str | None = None
    field_path: str | None = None


def _required_object(container: dict[str, Any], key: str, path: str) -> dict[str, Any]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise _ApiError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            f"{path}.{key} deve ser um objeto JSON",
            field_path=f"{path}.{key}",
        )
    return value


def _document(inputs: dict[str, Any], key: str) -> tuple[str, str]:
    document = _required_object(inputs, key, "inputs")
    source = document.get("source")
    content = document.get("content")
    if not isinstance(source, str) or not source:
        raise _ApiError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            f"inputs.{key}.source deve ser uma string não vazia",
            input_name=key,
            field_path=f"inputs.{key}.source",
        )
    if not isinstance(content, str):
        raise _ApiError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            f"inputs.{key}.content deve ser uma string",
            input_name=key,
            field_path=f"inputs.{key}.content",
        )
    return source, content


def _parsed_document(
    inputs: dict[str, Any],
    key: str,
    parser: Any,
) -> tuple[object, str]:
    source, content = _document(inputs, key)
    try:
        return parser(content, source), source
    except (RankLabError, SelectionError, WeightedRankingError) as exc:
        raise _ApiError(
            HTTPStatus.UNPROCESSABLE_ENTITY,
            "validation_error",
            str(exc),
            input_name=key,
            field_path=getattr(exc, "field_path", None),
        ) from exc


def _audit_request(payload: object) -> AuditReportRequest:
    if not isinstance(payload, dict):
        raise _ApiError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            "a requisição deve conter um objeto JSON",
        )
    inputs = _required_object(payload, "inputs", "request")
    parameters = _required_object(payload, "parameters", "request")

    matrix, matrix_source = _parsed_document(inputs, "matrix", parse_matrix)
    first, first_source = _parsed_document(
        inputs, "first_ranking", parse_ranking
    )
    second, second_source = _parsed_document(
        inputs, "second_ranking", parse_ranking
    )
    base_weights, base_source = _parsed_document(
        inputs, "base_weights", parse_weights
    )
    changed_weights, changed_source = _parsed_document(
        inputs, "changed_weights", parse_weights
    )

    closest_criteria = parameters.get("closest_criteria")
    if (
        not isinstance(closest_criteria, list)
        or len(closest_criteria) != 2
        or any(not isinstance(value, str) for value in closest_criteria)
    ):
        raise _ApiError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            "parameters.closest_criteria deve conter duas strings",
            input_name="closest_criteria",
            field_path="parameters.closest_criteria",
        )

    selection = _required_object(parameters, "selection", "parameters")
    selection_source = _required_object(selection, "source", "parameters.selection")
    source_type = selection_source.get("type")
    selection_criterion: str | None = None
    selection_values: list[object] | None = None
    selection_values_source: str | None = None
    if source_type == "matrix_criterion":
        criterion_id = selection_source.get("criterion_id")
        if not isinstance(criterion_id, str) or not criterion_id:
            raise _ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_request",
                "parameters.selection.source.criterion_id deve ser uma string não vazia",
                input_name="selection",
                field_path="parameters.selection.source.criterion_id",
            )
        selection_criterion = criterion_id
    elif source_type == "json_list":
        parsed_values, selection_values_source = _parsed_document(
            inputs,
            "selection_values",
            parse_selection_values,
        )
        selection_values = parsed_values  # type: ignore[assignment]
    else:
        raise _ApiError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            "parameters.selection.source.type deve ser matrix_criterion ou json_list",
            input_name="selection",
            field_path="parameters.selection.source.type",
        )

    has_order = "k" in selection
    has_percentile = "percentile" in selection
    if has_order == has_percentile:
        raise _ApiError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            "parameters.selection deve informar exatamente k ou percentile",
            input_name="selection",
            field_path="parameters.selection",
        )

    include_traces = parameters.get("include_traces", False)
    if not isinstance(include_traces, bool):
        raise _ApiError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            "parameters.include_traces deve ser booleano",
            input_name="include_traces",
            field_path="parameters.include_traces",
        )

    return AuditReportRequest(
        matrix=matrix,  # type: ignore[arg-type]
        matrix_source=matrix_source,
        first_ranking=first,  # type: ignore[arg-type]
        first_ranking_source=first_source,
        second_ranking=second,  # type: ignore[arg-type]
        second_ranking_source=second_source,
        base_weights=base_weights,  # type: ignore[arg-type]
        base_weights_source=base_source,
        changed_weights=changed_weights,  # type: ignore[arg-type]
        changed_weights_source=changed_source,
        closest_criteria=(closest_criteria[0], closest_criteria[1]),
        selection_criterion=selection_criterion,
        selection_values=selection_values,
        selection_values_source=selection_values_source,
        selection_order=selection.get("k") if has_order else None,
        selection_percentile=(
            selection.get("percentile") if has_percentile else None
        ),
        include_traces=include_traces,
    )


def _weight_sensitivity_request(payload: object) -> WeightSensitivityRequest:
    if not isinstance(payload, dict):
        raise _ApiError(
            HTTPStatus.BAD_REQUEST,
            "invalid_request",
            "a requisição deve conter um objeto JSON",
        )
    inputs = _required_object(payload, "inputs", "request")
    matrix, _ = _parsed_document(inputs, "matrix", parse_matrix)
    base_weights, _ = _parsed_document(inputs, "base_weights", parse_weights)
    changed_weights, _ = _parsed_document(inputs, "changed_weights", parse_weights)
    return WeightSensitivityRequest(
        matrix=matrix,  # type: ignore[arg-type]
        base_weights=base_weights,  # type: ignore[arg-type]
        changed_weights=changed_weights,  # type: ignore[arg-type]
    )


def _example_payload() -> dict[str, Any]:
    """Retorna apenas os arquivos de demonstração explicitamente permitidos."""

    example_root = REPOSITORY_ROOT / "examples"
    inputs = {
        key: {
            "source": str(Path("examples") / filename),
            "content": (example_root / filename).read_text(encoding="utf-8"),
        }
        for key, filename in EXAMPLE_INPUTS.items()
    }
    return {
        "inputs": inputs,
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


def _build_handler(report_path: Path | None) -> type[BaseHTTPRequestHandler]:
    class ViewerHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - nome exigido por BaseHTTPRequestHandler
            path = urlsplit(self.path).path
            if path == "/api/report":
                self._send_report()
            elif path == "/api/examples/audit-report":
                try:
                    self._send_json(HTTPStatus.OK, _example_payload())
                except OSError:
                    self._send_api_error(
                        _ApiError(
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                            "examples_unavailable",
                            "não foi possível carregar os arquivos de demonstração",
                        )
                    )
            elif path in STATIC_FILES:
                filename, content_type = STATIC_FILES[path]
                body = files("ranklab").joinpath("web", filename).read_bytes()
                self._send(HTTPStatus.OK, content_type, body)
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "recurso não encontrado"})

        def do_POST(self) -> None:  # noqa: N802 - nome exigido por BaseHTTPRequestHandler
            path = urlsplit(self.path).path
            if path not in {"/api/report", "/api/weight-sensitivity"}:
                self._send_api_error(
                    _ApiError(
                        HTTPStatus.NOT_FOUND,
                        "not_found",
                        "recurso não encontrado",
                    )
                )
                return
            try:
                payload = self._read_json_request()
                if path == "/api/report":
                    response = generate_audit_report(_audit_request(payload))
                else:
                    response = generate_weight_sensitivity(
                        _weight_sensitivity_request(payload)
                    )
            except _ApiError as exc:
                self._send_api_error(exc)
                return
            except RankingComparisonError as exc:
                self._send_api_error(
                    _ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "validation_error",
                        str(exc),
                        input_name="rankings",
                    )
                )
                return
            except ClosestPairError as exc:
                self._send_api_error(
                    _ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "validation_error",
                        str(exc),
                        input_name="closest_criteria",
                        field_path="parameters.closest_criteria",
                    )
                )
                return
            except SelectionError as exc:
                self._send_api_error(
                    _ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "validation_error",
                        str(exc),
                        input_name="selection",
                        field_path="parameters.selection",
                    )
                )
                return
            except WeightedRankingError as exc:
                self._send_api_error(
                    _ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "validation_error",
                        str(exc),
                        input_name="weights",
                    )
                )
                return
            except RankLabError as exc:
                self._send_api_error(
                    _ApiError(
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                        "validation_error",
                        str(exc),
                        field_path=exc.field_path,
                    )
                )
                return
            except Exception:
                self._send_api_error(
                    _ApiError(
                        HTTPStatus.INTERNAL_SERVER_ERROR,
                        "internal_error",
                        "não foi possível gerar o relatório",
                    )
                )
                return
            self._send_json(HTTPStatus.OK, response)

        def _discard_request_body(self, length: int) -> None:
            """Consome o corpo recusado para que o cliente consiga ler o erro 413.

            Fechar o socket com dados pendentes interrompe o envio do cliente com
            ``EPIPE`` antes de ele ler a resposta. O descarte não guarda o corpo e é
            limitado em bytes e em tempo, para um cliente lento não prender a thread.
            """

            remaining = min(length, MAX_DISCARDED_BYTES)
            self.connection.settimeout(DISCARD_TIMEOUT_SECONDS)
            try:
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 65_536))
                    if not chunk:
                        return
                    remaining -= len(chunk)
            except OSError:
                # Cliente parado ou desconectado: a resposta é tentada mesmo assim.
                return

        def _read_json_request(self) -> object:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
            if content_type != "application/json":
                raise _ApiError(
                    HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                    "unsupported_media_type",
                    "Content-Type deve ser application/json",
                )
            if self.headers.get("Transfer-Encoding"):
                raise _ApiError(
                    HTTPStatus.BAD_REQUEST,
                    "unsupported_transfer_encoding",
                    "Transfer-Encoding não é suportado",
                )
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                raise _ApiError(
                    HTTPStatus.LENGTH_REQUIRED,
                    "length_required",
                    "Content-Length é obrigatório",
                )
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise _ApiError(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_content_length",
                    "Content-Length deve ser um inteiro não negativo",
                ) from exc
            if length < 0:
                raise _ApiError(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_content_length",
                    "Content-Length deve ser um inteiro não negativo",
                )
            if length > MAX_REQUEST_BYTES:
                self._discard_request_body(length)
                raise _ApiError(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    "request_too_large",
                    f"a requisição excede o limite de {MAX_REQUEST_BYTES} bytes",
                )
            body = self.rfile.read(length)
            try:
                text = body.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise _ApiError(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_encoding",
                    "a requisição deve usar UTF-8",
                ) from exc
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise _ApiError(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_json",
                    f"JSON inválido: {exc.msg} "
                    f"(linha {exc.lineno}, coluna {exc.colno})",
                ) from exc

        def _send_api_error(self, error: _ApiError) -> None:
            payload: dict[str, Any] = {
                "code": error.code,
                "message": error.message,
            }
            if error.input_name is not None:
                payload["input"] = error.input_name
            if error.field_path is not None:
                payload["field_path"] = error.field_path
            self._send_json(error.status, {"error": payload})

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
