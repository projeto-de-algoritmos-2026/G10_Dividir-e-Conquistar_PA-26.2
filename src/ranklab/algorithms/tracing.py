"""Tipos comuns para rastreamentos didáticos dos algoritmos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

TRACE_ITEM_LIMIT = 100
"""Maior entrada para a qual o passo a passo é materializado."""

T = TypeVar("T")


@dataclass(frozen=True)
class TraceStep:
    """Um estado observável do algoritmo, acompanhado de explicação textual."""

    kind: str
    depth: int
    description: str
    state: dict[str, Any]


@dataclass(frozen=True)
class AlgorithmTrace:
    """Rastreamento disponível ou metadados que explicam sua omissão."""

    algorithm: str
    item_count: int
    steps: tuple[TraceStep, ...] | None
    limit: int = TRACE_ITEM_LIMIT
    reason: str | None = None

    @property
    def status(self) -> str:
        return "available" if self.steps is not None else "omitted"


@dataclass(frozen=True)
class TracedResult(Generic[T]):
    """Resultado normal junto do rastreamento opcional da mesma execução."""

    result: T
    trace: AlgorithmTrace


def available_trace(
    algorithm: str,
    item_count: int,
    steps: list[TraceStep],
) -> AlgorithmTrace:
    return AlgorithmTrace(algorithm, item_count, tuple(steps))


def omitted_trace(algorithm: str, item_count: int) -> AlgorithmTrace:
    return AlgorithmTrace(
        algorithm,
        item_count,
        None,
        reason="A entrada excede o limite de rastreamento.",
    )
