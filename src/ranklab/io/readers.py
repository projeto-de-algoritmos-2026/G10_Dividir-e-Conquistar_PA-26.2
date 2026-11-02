"""Leitores de arquivos RankLab.

Funções públicas
-----------------
parse_ranking(content, source) → Ranking
load_ranking(path)              → Ranking
parse_matrix(content, source)   → ScoringMatrix
load_matrix(path)               → ScoringMatrix
assert_same_item_set(a, b) → None  (levanta RankLabError se os conjuntos diferirem)

Toda entrada inválida levanta ``RankLabError`` com arquivo, caminho do campo e
motivo — nenhuma entrada inválida é convertida silenciosamente.
"""

from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path

from ranklab.domain.models import (
    Criterion,
    Direction,
    MatrixItem,
    Ranking,
    RankingItem,
    ScoringMatrix,
)
from ranklab.io.errors import RankLabError

# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

_RANKING_REQUIRED = ("format_version", "ranking_id", "name", "origin", "items")
_MATRIX_REQUIRED = ("format_version", "matrix_id", "name", "origin", "criteria", "items")
_CRITERION_REQUIRED = ("criterion_id", "name", "direction", "unit")
_VALID_DIRECTIONS = frozenset(d.value for d in Direction)


def _parse_json_object(content: str, source: str) -> dict:
    """Decodifica um objeto JSON já recebido, preservando sua origem."""

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RankLabError(
            source,
            f"JSON inválido: {exc.msg} (linha {exc.lineno}, col {exc.colno})",
        ) from exc
    if not isinstance(data, dict):
        raise RankLabError(source, "o conteúdo do arquivo deve ser um objeto JSON")
    return data


def _read_text(path: str | Path) -> tuple[str, str]:
    """Lê UTF-8 de um arquivo e retorna conteúdo e nome usado nos erros."""

    resolved = Path(path)
    filename = resolved.name
    try:
        return resolved.read_text(encoding="utf-8"), filename
    except FileNotFoundError as exc:
        raise RankLabError(filename, "arquivo não encontrado") from exc
    except UnicodeDecodeError as exc:
        raise RankLabError(filename, "arquivo não é UTF-8 válido") from exc
    except OSError as exc:
        raise RankLabError(filename, f"erro ao ler arquivo: {exc}") from exc


# ---------------------------------------------------------------------------
# Leitor de ranking
# ---------------------------------------------------------------------------

def _validate_ranking(data: dict, filename: str) -> Ranking:
    """Valida *data* como ranking v1 e retorna um objeto ``Ranking``."""

    # --- campos obrigatórios no topo ---
    for field in _RANKING_REQUIRED:
        if field not in data:
            raise RankLabError(filename, f"campo obrigatório ausente: {field!r}")

    # --- format_version ---
    fv = data["format_version"]
    if fv != 1:
        raise RankLabError(filename, f"format_version não suportado: {fv!r}; esperado 1",
                           "format_version")

    # --- items deve ser lista não-vazia ---
    items_raw = data["items"]
    if not isinstance(items_raw, list) or len(items_raw) == 0:
        raise RankLabError(filename, "items deve ser uma lista não-vazia", "items")

    seen_ids: set[str] = set()
    seen_positions: set[int] = set()
    validated_items: list[RankingItem] = []

    for idx, item in enumerate(items_raw):
        prefix = f"items[{idx}]"

        if not isinstance(item, dict):
            raise RankLabError(filename, "cada item deve ser um objeto JSON", prefix)

        # item_id
        if "item_id" not in item:
            raise RankLabError(filename, "campo obrigatório ausente: 'item_id'", prefix)
        item_id = item["item_id"]
        if not isinstance(item_id, str) or not item_id:
            raise RankLabError(filename, "item_id deve ser uma string não-vazia",
                               f"{prefix}.item_id")
        if item_id in seen_ids:
            raise RankLabError(filename, f"item_id duplicado: {item_id!r}",
                               f"{prefix}.item_id")
        seen_ids.add(item_id)

        # position
        if "position" not in item:
            raise RankLabError(filename, "campo obrigatório ausente: 'position'", prefix)
        position = item["position"]
        # JSON não tem inteiro vs. float, mas o contrato exige inteiro sem arredondamento
        if not isinstance(position, int) or isinstance(position, bool):
            raise RankLabError(filename,
                               "position deve ser um inteiro (sem ponto decimal, sem booleano)",
                               f"{prefix}.position")
        if position < 1:
            raise RankLabError(filename,
                               f"position deve ser ≥ 1; encontrado {position}",
                               f"{prefix}.position")
        if position in seen_positions:
            raise RankLabError(filename,
                               f"posição duplicada: {position}",
                               f"{prefix}.position")
        seen_positions.add(position)

        validated_items.append(RankingItem(item_id=item_id, position=position))

    # --- conjunto de posições deve ser exatamente {1…n} ---
    n = len(validated_items)
    expected = set(range(1, n + 1))
    if seen_positions != expected:
        missing = sorted(expected - seen_positions)
        extra = sorted(seen_positions - expected)
        parts = []
        if missing:
            parts.append(f"ausentes: {missing}")
        if extra:
            parts.append(f"fora do intervalo: {extra}")
        raise RankLabError(filename,
                           f"posições não formam o conjunto {{1…{n}}}; {'; '.join(parts)}",
                           "items")

    sorted_items = tuple(sorted(validated_items, key=lambda it: it.position))
    return Ranking(
        ranking_id=data["ranking_id"],
        name=data["name"],
        origin=data["origin"],
        items=sorted_items,
    )


def load_ranking(path: str | Path) -> Ranking:
    """Carrega e valida um arquivo de ranking JSON v1.

    Levanta ``RankLabError`` para qualquer arquivo inválido.
    """
    content, filename = _read_text(path)
    if Path(path).suffix.lower() == ".csv":
        return parse_ranking_csv(content, filename)
    return parse_ranking(content, filename)


def parse_ranking(content: str, source: str = "ranking.json") -> Ranking:
    """Valida um ranking recebido como texto JSON, sem acessar arquivos."""

    return _validate_ranking(_parse_json_object(content, source), source)


def _csv_metadata(content: str, source: str) -> tuple[dict, str]:
    lines = content.splitlines()
    if not lines or not lines[0].startswith("#"):
        raise RankLabError(
            source,
            "a primeira linha deve conter metadados JSON iniciados por '#'",
            "linha 1",
        )
    raw = lines[0][1:].strip()
    try:
        metadata = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RankLabError(
            source, f"metadados JSON inválidos: {exc.msg}", f"linha 1, coluna {exc.colno}"
        ) from exc
    if not isinstance(metadata, dict):
        raise RankLabError(source, "metadados devem ser um objeto JSON", "linha 1")
    return metadata, "\n".join(lines[1:])


def _csv_reader(content: str, source: str) -> tuple[dict, list[list[str]]]:
    metadata, rows_content = _csv_metadata(content, source)
    try:
        rows = list(csv.reader(io.StringIO(rows_content), strict=True))
    except csv.Error as exc:
        line = getattr(exc, "lineno", 1) + 1
        raise RankLabError(source, f"CSV inválido: {exc}", f"linha {line}") from exc
    if not rows or not rows[0]:
        raise RankLabError(source, "cabeçalho CSV ausente", "linha 2")
    return metadata, rows


def _csv_error(source: str, line: int, column: int, reason: str) -> RankLabError:
    return RankLabError(source, reason, f"linha {line}, coluna {column}")


def _localize_csv_validation_error(error: RankLabError, source: str) -> RankLabError:
    """Converte o caminho JSON produzido pelo validador em linha/coluna CSV."""

    path = error.field_path or ""
    line, column = 1, 1
    if path.startswith("items["):
        try:
            item_index = int(path.split("[", 1)[1].split("]", 1)[0])
        except ValueError:
            item_index = 0
        line = item_index + 3
        column = 1 if ".values." not in path and not path.endswith("position") else 2
        if ".values." in path:
            column = 2
    return _csv_error(source, line, column, error.reason)


def parse_ranking_csv(content: str, source: str = "ranking.csv") -> Ranking:
    """Valida um ranking CSV v1 com metadados na primeira linha."""

    metadata, rows = _csv_reader(content, source)
    header = rows[0]
    if header != ["item_id", "position"]:
        raise _csv_error(source, 2, 1, "cabeçalho esperado: item_id,position")
    items = []
    for row_index, row in enumerate(rows[1:], start=3):
        if len(row) != 2:
            raise _csv_error(source, row_index, len(row) + 1, "cada linha deve ter 2 colunas")
        item_id, position = row
        if not item_id:
            raise _csv_error(source, row_index, 1, "item_id não pode ser vazio")
        if not position:
            raise _csv_error(source, row_index, 2, "position não pode ser vazia")
        try:
            parsed_position = int(position)
        except ValueError as exc:
            raise _csv_error(source, row_index, 2, "position deve ser um inteiro") from exc
        if any(item["item_id"] == item_id for item in items):
            raise _csv_error(source, row_index, 1, f"item_id duplicado: {item_id!r}")
        items.append({"item_id": item_id, "position": parsed_position})
    metadata = {**metadata, "items": items}
    try:
        return _validate_ranking(metadata, source)
    except RankLabError as exc:
        raise _localize_csv_validation_error(exc, source) from exc


def load_ranking_csv(path: str | Path) -> Ranking:
    """Carrega e valida um ranking CSV pelo caminho informado."""

    content, filename = _read_text(path)
    return parse_ranking_csv(content, filename)


# ---------------------------------------------------------------------------
# Leitor de matriz de pontuação
# ---------------------------------------------------------------------------

def _validate_matrix(data: dict, filename: str) -> ScoringMatrix:
    """Valida *data* como matriz de pontuação v1 e retorna ``ScoringMatrix``."""

    # --- campos obrigatórios no topo ---
    for field in _MATRIX_REQUIRED:
        if field not in data:
            raise RankLabError(filename, f"campo obrigatório ausente: {field!r}")

    # --- format_version ---
    fv = data["format_version"]
    if fv != 1:
        raise RankLabError(filename, f"format_version não suportado: {fv!r}; esperado 1",
                           "format_version")

    # --- criteria ---
    criteria_raw = data["criteria"]
    if not isinstance(criteria_raw, list) or len(criteria_raw) == 0:
        raise RankLabError(filename, "criteria deve ser uma lista não-vazia", "criteria")

    seen_criterion_ids: set[str] = set()
    validated_criteria: list[Criterion] = []

    for idx, crit in enumerate(criteria_raw):
        prefix = f"criteria[{idx}]"
        if not isinstance(crit, dict):
            raise RankLabError(filename, "cada critério deve ser um objeto JSON", prefix)

        for field in _CRITERION_REQUIRED:
            if field not in crit:
                raise RankLabError(filename, f"campo obrigatório ausente: {field!r}",
                                   prefix)

        cid = crit["criterion_id"]
        if not isinstance(cid, str) or not cid:
            raise RankLabError(filename, "criterion_id deve ser uma string não-vazia",
                               f"{prefix}.criterion_id")
        if cid in seen_criterion_ids:
            raise RankLabError(filename, f"criterion_id duplicado: {cid!r}",
                               f"{prefix}.criterion_id")
        seen_criterion_ids.add(cid)

        direction_raw = crit["direction"]
        if direction_raw not in _VALID_DIRECTIONS:
            raise RankLabError(filename,
                               f"direction inválido: {direction_raw!r}; "
                               f"valores aceitos: {sorted(_VALID_DIRECTIONS)}",
                               f"{prefix}.direction")

        validated_criteria.append(Criterion(
            criterion_id=cid,
            name=crit["name"],
            direction=Direction(direction_raw),
            unit=crit["unit"],
        ))

    # --- items ---
    items_raw = data["items"]
    if not isinstance(items_raw, list) or len(items_raw) == 0:
        raise RankLabError(filename, "items deve ser uma lista não-vazia", "items")

    seen_item_ids: set[str] = set()
    validated_items: list[MatrixItem] = []

    for idx, item in enumerate(items_raw):
        prefix = f"items[{idx}]"
        if not isinstance(item, dict):
            raise RankLabError(filename, "cada item deve ser um objeto JSON", prefix)

        if "item_id" not in item:
            raise RankLabError(filename, "campo obrigatório ausente: 'item_id'", prefix)
        item_id = item["item_id"]
        if not isinstance(item_id, str) or not item_id:
            raise RankLabError(filename, "item_id deve ser uma string não-vazia",
                               f"{prefix}.item_id")
        if item_id in seen_item_ids:
            raise RankLabError(filename, f"item_id duplicado: {item_id!r}",
                               f"{prefix}.item_id")
        seen_item_ids.add(item_id)

        if "values" not in item:
            raise RankLabError(filename, "campo obrigatório ausente: 'values'", prefix)
        values_raw = item["values"]
        if not isinstance(values_raw, dict):
            raise RankLabError(filename, "values deve ser um objeto JSON",
                               f"{prefix}.values")

        # critérios presentes vs. declarados
        declared = seen_criterion_ids
        provided = set(values_raw.keys())
        missing_crit = declared - provided
        extra_crit = provided - declared

        if missing_crit:
            for cid in sorted(missing_crit):
                raise RankLabError(filename, "valor ausente",
                                   f"{prefix}.values.{cid}")
        if extra_crit:
            for cid in sorted(extra_crit):
                raise RankLabError(filename,
                                   f"critério desconhecido: {cid!r}",
                                   f"{prefix}.values.{cid}")

        # validar cada valor numérico
        values: dict[str, float] = {}
        for cid in sorted(declared):
            val = values_raw[cid]
            field_path = f"{prefix}.values.{cid}"
            # rejeita bool (subclasse de int em Python), None, strings
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise RankLabError(filename,
                                   f"valor deve ser um número; encontrado {type(val).__name__!r}",
                                   field_path)
            # rejeita NaN e infinitos (não são números JSON válidos, mas json.loads os rejeita
            # de qualquer forma; este check defende contra construção programática)
            if not math.isfinite(val):
                raise RankLabError(filename,
                                   f"valor não-finito não é permitido: {val}",
                                   field_path)
            values[cid] = float(val)

        validated_items.append(MatrixItem(item_id=item_id, values=values))

    return ScoringMatrix(
        matrix_id=data["matrix_id"],
        name=data["name"],
        origin=data["origin"],
        criteria=tuple(validated_criteria),
        items=tuple(validated_items),
    )


def load_matrix(path: str | Path) -> ScoringMatrix:
    """Carrega e valida um arquivo de matriz de pontuação JSON v1.

    Levanta ``RankLabError`` para qualquer arquivo inválido.
    """
    content, filename = _read_text(path)
    if Path(path).suffix.lower() == ".csv":
        return parse_matrix_csv(content, filename)
    return parse_matrix(content, filename)


def parse_matrix(content: str, source: str = "matriz.json") -> ScoringMatrix:
    """Valida uma matriz recebida como texto JSON, sem acessar arquivos."""

    return _validate_matrix(_parse_json_object(content, source), source)


def parse_matrix_csv(content: str, source: str = "matriz.csv") -> ScoringMatrix:
    """Valida uma matriz CSV v1 com critérios descritos nos metadados."""

    metadata, rows = _csv_reader(content, source)
    header = rows[0]
    if len(header) < 2 or header[0] != "item_id":
        raise _csv_error(source, 2, 1, "cabeçalho deve começar por item_id")
    criterion_ids = header[1:]
    if len(set(criterion_ids)) != len(criterion_ids) or any(not item for item in criterion_ids):
        raise _csv_error(source, 2, 1, "critérios do cabeçalho devem ser únicos e não vazios")
    criteria = metadata.get("criteria")
    if not isinstance(criteria, list):
        raise RankLabError(source, "metadados devem conter a lista 'criteria'", "linha 1")
    metadata_criteria = [criterion.get("criterion_id") for criterion in criteria
                         if isinstance(criterion, dict)]
    if metadata_criteria != criterion_ids:
        raise _csv_error(
            source, 2, 2,
            "colunas de critérios devem coincidir, na mesma ordem, com os metadados",
        )
    items = []
    seen: set[str] = set()
    for row_index, row in enumerate(rows[1:], start=3):
        if len(row) != len(header):
            raise _csv_error(
                source, row_index, len(row) + 1,
                f"cada linha deve ter {len(header)} colunas",
            )
        item_id = row[0]
        if not item_id:
            raise _csv_error(source, row_index, 1, "item_id não pode ser vazio")
        if item_id in seen:
            raise _csv_error(source, row_index, 1, f"item_id duplicado: {item_id!r}")
        seen.add(item_id)
        values = {}
        for column, (criterion_id, raw_value) in enumerate(zip(criterion_ids, row[1:]), start=2):
            if not raw_value:
                raise _csv_error(source, row_index, column, "célula vazia não é permitida")
            try:
                value = float(raw_value)
            except ValueError as exc:
                raise _csv_error(
                    source, row_index, column,
                    "valor deve usar ponto decimal (separador decimal ',' é ambíguo)",
                ) from exc
            if not math.isfinite(value):
                raise _csv_error(source, row_index, column, "valor não-finito não é permitido")
            values[criterion_id] = value
        items.append({"item_id": item_id, "values": values})
    metadata = {**metadata, "items": items}
    try:
        return _validate_matrix(metadata, source)
    except RankLabError as exc:
        raise _localize_csv_validation_error(exc, source) from exc


def load_matrix_csv(path: str | Path) -> ScoringMatrix:
    """Carrega e valida uma matriz CSV pelo caminho informado."""

    content, filename = _read_text(path)
    return parse_matrix_csv(content, filename)


# ---------------------------------------------------------------------------
# Validação cruzada de rankings
# ---------------------------------------------------------------------------

def assert_same_item_set(a: Ranking, b: Ranking) -> None:
    """Verifica que dois rankings contêm exatamente o mesmo conjunto de item_ids.

    Levanta ``RankLabError`` se os conjuntos diferirem, listando os IDs que
    aparecem em apenas um dos rankings.
    """
    ids_a = {it.item_id for it in a.items}
    ids_b = {it.item_id for it in b.items}
    diff = ids_a.symmetric_difference(ids_b)
    if diff:
        only_a = sorted(ids_a - ids_b)
        only_b = sorted(ids_b - ids_a)
        parts = []
        if only_a:
            parts.append(f"apenas em '{a.ranking_id}': {only_a}")
        if only_b:
            parts.append(f"apenas em '{b.ranking_id}': {only_b}")
        raise RankLabError(
            f"[{a.ranking_id}, {b.ranking_id}]",
            f"os rankings não compartilham o mesmo conjunto de item_ids; {'; '.join(parts)}",
        )
