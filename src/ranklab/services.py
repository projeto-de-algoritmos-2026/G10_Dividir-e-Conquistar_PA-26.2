"""Serviços de aplicação compartilhados pela CLI e pela API local."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ranklab.algorithms import (
    SelectionError,
    closest_pair,
    compare_rankings,
    compare_weight_scenarios,
    select_k,
    select_percentile,
    trace_closest_pair,
    trace_ranking_comparison,
    trace_select_k,
    trace_select_percentile,
)
from ranklab.domain.models import Ranking, ScoringMatrix
from ranklab.reporting import (
    build_audit_report,
    build_weight_sensitivity_response,
)


@dataclass(frozen=True)
class AuditReportRequest:
    """Entradas validadas e parâmetros necessários ao relatório completo."""

    matrix: ScoringMatrix
    matrix_source: str
    first_ranking: Ranking
    first_ranking_source: str
    second_ranking: Ranking
    second_ranking_source: str
    base_weights: dict[str, object]
    base_weights_source: str
    changed_weights: dict[str, object]
    changed_weights_source: str
    closest_criteria: tuple[str, str]
    selection_criterion: str | None = None
    selection_values: list[object] | None = None
    selection_values_source: str | None = None
    selection_order: int | None = None
    selection_percentile: float | None = None
    include_traces: bool = False


@dataclass(frozen=True)
class WeightSensitivityRequest:
    """Entradas validadas para comparar dois cenários de pesos."""

    matrix: ScoringMatrix
    base_weights: dict[str, object]
    changed_weights: dict[str, object]


def generate_weight_sensitivity(
    request: WeightSensitivityRequest,
) -> dict[str, Any]:
    """Executa a mesma comparação usada por ``compare-weights``."""

    result = compare_weight_scenarios(
        request.matrix,
        request.base_weights,  # type: ignore[arg-type]
        request.changed_weights,  # type: ignore[arg-type]
    )
    return build_weight_sensitivity_response(request.matrix, result)


def generate_audit_report(request: AuditReportRequest) -> dict[str, Any]:
    """Executa as quatro análises e constrói o relatório auditável.

    A função não acessa arquivos nem conhece HTTP. CLI e servidor apenas
    convertem suas entradas para :class:`AuditReportRequest`.
    """

    traces = None
    if request.include_traces:
        ranking_run = trace_ranking_comparison(
            request.first_ranking,
            request.second_ranking,
        )
        closest_run = trace_closest_pair(request.matrix, request.closest_criteria)
        ranking_comparison = ranking_run.result
        closest = closest_run.result
        traces = {
            "ordering_divergence": ranking_run.trace,
            "proximity": closest_run.trace,
        }
    else:
        ranking_comparison = compare_rankings(
            request.first_ranking,
            request.second_ranking,
        )
        closest = closest_pair(request.matrix, request.closest_criteria)

    if (request.selection_criterion is None) == (request.selection_values is None):
        raise SelectionError(
            "informe exatamente uma fonte de seleção: critério ou lista JSON"
        )

    if request.selection_criterion is not None:
        criteria = {
            criterion.criterion_id: criterion
            for criterion in request.matrix.criteria
        }
        criterion = criteria.get(request.selection_criterion)
        if criterion is None:
            raise SelectionError(
                "selection-criterion deve identificar um critério "
                f"existente: {request.selection_criterion!r}"
            )
        values: list[object] = [
            item.values[request.selection_criterion]
            for item in request.matrix.items
        ]
        selection_source: dict[str, Any] = {
            "type": "matrix_criterion",
            "criterion_id": criterion.criterion_id,
            "name": criterion.name,
            "unit": criterion.unit,
            "item_count": len(values),
        }
    else:
        values = list(request.selection_values or [])
        selection_source = {
            "type": "json_list",
            "path": request.selection_values_source or "valores.json",
            "item_count": len(values),
        }

    if (request.selection_order is None) == (request.selection_percentile is None):
        raise SelectionError("informe exatamente uma ordem k ou um percentil")
    if request.include_traces:
        selection_run = (
            trace_select_k(values, request.selection_order)
            if request.selection_order is not None
            else trace_select_percentile(values, request.selection_percentile)
        )
        selection = selection_run.result
        assert traces is not None
        traces["order_selection"] = selection_run.trace
    else:
        selection = (
            select_k(values, request.selection_order)
            if request.selection_order is not None
            else select_percentile(values, request.selection_percentile)
        )

    sensitivity = compare_weight_scenarios(
        request.matrix,
        request.base_weights,  # type: ignore[arg-type]
        request.changed_weights,  # type: ignore[arg-type]
    )
    return build_audit_report(
        matrix=request.matrix,
        matrix_path=request.matrix_source,
        first_ranking=request.first_ranking,
        first_ranking_path=request.first_ranking_source,
        second_ranking=request.second_ranking,
        second_ranking_path=request.second_ranking_source,
        ranking_comparison=ranking_comparison,
        closest=closest,
        closest_criteria=request.closest_criteria,
        selection=selection,
        selection_values=values,
        selection_source=selection_source,
        sensitivity=sensitivity,
        base_weights_path=request.base_weights_source,
        changed_weights_path=request.changed_weights_source,
        traces=traces,
    )
