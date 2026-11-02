"""Leitura de entradas JSON auxiliares usadas pelas análises.

As funções ``parse_*`` validam conteúdo já recebido, enquanto ``load_*`` são
adaptadores de arquivo mantidos para a CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

from ranklab.algorithms import SelectionError, WeightedRankingError


def _read_text(path: Path, error_type: type[ValueError]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise error_type(f"{path}: arquivo não encontrado") from exc
    except UnicodeDecodeError as exc:
        raise error_type(f"{path}: arquivo não é UTF-8 válido") from exc
    except OSError as exc:
        raise error_type(f"{path}: não foi possível ler o arquivo: {exc}") from exc


def _decode(content: str, source: str, error_type: type[ValueError]) -> object:
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise error_type(
            f"{source}: JSON inválido: {exc.msg} "
            f"(linha {exc.lineno}, coluna {exc.colno})"
        ) from exc


def parse_weights(content: str, source: str = "pesos.json") -> dict[str, object]:
    """Decodifica um objeto JSON de pesos sem acessar arquivos."""

    weights = _decode(content, source, WeightedRankingError)
    if not isinstance(weights, dict):
        raise WeightedRankingError(
            f"{source}: o arquivo de pesos deve conter um objeto JSON"
        )
    return weights


def load_weights(path: Path) -> dict[str, object]:
    """Lê um objeto JSON de pesos com as mensagens históricas da CLI."""

    return parse_weights(_read_text(path, WeightedRankingError), str(path))


def parse_selection_values(
    content: str,
    source: str = "valores.json",
) -> list[object]:
    """Decodifica uma lista JSON para seleção sem acessar arquivos."""

    values = _decode(content, source, SelectionError)
    if not isinstance(values, list):
        raise SelectionError(
            f"{source}: o arquivo de seleção deve conter uma lista JSON"
        )
    return values


def load_selection_values(path: Path) -> list[object]:
    """Lê uma lista JSON para seleção com as mensagens históricas da CLI."""

    return parse_selection_values(_read_text(path, SelectionError), str(path))
