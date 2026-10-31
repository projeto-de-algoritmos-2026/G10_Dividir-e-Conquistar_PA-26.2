"""Leitores de arquivos RankLab.

Funções públicas
----------------
load_ranking(path)        → Ranking
load_matrix(path)         → ScoringMatrix
assert_same_item_set(a, b) → None  (levanta RankLabError se os conjuntos diferirem)

Toda entrada inválida levanta ``RankLabError`` com arquivo, caminho do campo e
motivo — nenhuma entrada inválida é convertida silenciosamente.
"""

from __future__ import annotations

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


def _load_json(path: str | Path) -> tuple[dict, str]:
    """Abre e decodifica um arquivo JSON, levantando RankLabError em falhas."""
    path = Path(path)
    filename = path.name
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RankLabError(filename, "arquivo não encontrado")
    except OSError as exc:
        raise RankLabError(filename, f"erro ao ler arquivo: {exc}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RankLabError(filename, f"JSON inválido: {exc.msg} (linha {exc.lineno}, col {exc.colno})")
    if not isinstance(data, dict):
        raise RankLabError(filename, "o conteúdo do arquivo deve ser um objeto JSON")
    return data, filename


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
    data, filename = _load_json(path)
    return _validate_ranking(data, filename)


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
    data, filename = _load_json(path)
    return _validate_matrix(data, filename)


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
