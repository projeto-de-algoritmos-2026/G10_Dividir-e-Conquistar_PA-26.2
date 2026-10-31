"""Modelos de domínio do RankLab.

Estes dataclasses representam o modelo comum que os leitores produzem após
validação. São imutáveis: toda validação acontece nos leitores de IO, não aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Direction(str, Enum):
    """Direção de preferência de um critério."""

    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"


@dataclass(frozen=True)
class RankingItem:
    """Um item dentro de um ranking estrito."""

    item_id: str
    position: int


@dataclass(frozen=True)
class Ranking:
    """Ranking estrito v1.

    ``items`` é armazenado ordenado por ``position`` de forma crescente.
    """

    ranking_id: str
    name: str
    origin: str
    items: tuple[RankingItem, ...]


@dataclass(frozen=True)
class Criterion:
    """Definição de um critério numa matriz de pontuação."""

    criterion_id: str
    name: str
    direction: Direction
    unit: str


@dataclass(frozen=True)
class MatrixItem:
    """Uma linha de pontuação na matriz.

    ``values`` mapeia ``criterion_id`` → valor numérico.
    """

    item_id: str
    values: dict[str, float]

    def __hash__(self) -> int:  # needed because dict is not hashable by default
        return hash((self.item_id, tuple(sorted(self.values.items()))))


@dataclass(frozen=True)
class ScoringMatrix:
    """Matriz de pontuação multicritério v1."""

    matrix_id: str
    name: str
    origin: str
    criteria: tuple[Criterion, ...]
    items: tuple[MatrixItem, ...]
