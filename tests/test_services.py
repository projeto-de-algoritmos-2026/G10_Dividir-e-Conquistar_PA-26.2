from __future__ import annotations

from pathlib import Path

import pytest

from ranklab.io.analysis_inputs import load_weights
from ranklab.io.readers import load_matrix, load_ranking, parse_matrix, parse_ranking
from ranklab.reporting import ORDER_SELECTION_DISPLAY_LIMIT
from ranklab.services import AuditReportRequest, generate_audit_report

REPOSITORY_ROOT = Path(__file__).parent.parent


def _request(
    values: list[object],
    *,
    order: int | None = None,
    percentile: float | None = None,
) -> AuditReportRequest:
    return AuditReportRequest(
        matrix=load_matrix(REPOSITORY_ROOT / "examples" / "matriz.json"),
        matrix_source="examples/matriz.json",
        first_ranking=load_ranking(REPOSITORY_ROOT / "examples" / "ranking.json"),
        first_ranking_source="examples/ranking.json",
        second_ranking=load_ranking(
            REPOSITORY_ROOT / "examples" / "ranking-operacional.json"
        ),
        second_ranking_source="examples/ranking-operacional.json",
        base_weights=load_weights(REPOSITORY_ROOT / "examples" / "pesos.json"),
        base_weights_source="examples/pesos.json",
        changed_weights=load_weights(
            REPOSITORY_ROOT / "examples" / "pesos-alterados-muda.json"
        ),
        changed_weights_source="examples/pesos-alterados-muda.json",
        closest_criteria=("qualidade", "prazo_dias"),
        selection_values=values,
        selection_values_source="valores.json",
        selection_order=order,
        selection_percentile=percentile,
    )


def test_content_readers_match_file_adapters() -> None:
    matrix_path = REPOSITORY_ROOT / "examples" / "matriz.json"
    ranking_path = REPOSITORY_ROOT / "examples" / "ranking.json"

    assert parse_matrix(matrix_path.read_text(encoding="utf-8"), matrix_path.name) == (
        load_matrix(matrix_path)
    )
    assert parse_ranking(
        ranking_path.read_text(encoding="utf-8"), ranking_path.name
    ) == load_ranking(ranking_path)


@pytest.mark.parametrize(
    ("values", "order", "expected"),
    [
        ([4, 2, 4, 1], 3, [1, 2, 4, 4]),
        ([7], 1, [7]),
    ],
)
def test_order_selection_display_preserves_values_and_duplicates(
    values: list[object], order: int, expected: list[object]
) -> None:
    report = generate_audit_report(_request(values, order=order))
    selection = report["analyses"]["order_selection"]

    assert selection["display"]["ordered_values"] == expected
    assert selection["display"]["omitted"] is False
    assert selection["value"] == expected[order - 1]


def test_order_selection_reports_percentile_conversion() -> None:
    report = generate_audit_report(_request([9, 2, 7, 4], percentile=50))
    selection = report["analyses"]["order_selection"]

    assert selection["order"] == 2
    assert selection["percentile_conversion"] == {
        "rule": "max(1, ceil(percentile * item_count / 100))",
        "percentile": 50.0,
        "item_count": 4,
        "order": 2,
    }


def test_order_selection_omits_collection_above_display_limit() -> None:
    values = list(range(ORDER_SELECTION_DISPLAY_LIMIT + 1))
    report = generate_audit_report(_request(values, order=1))
    display = report["analyses"]["order_selection"]["display"]

    assert display["ordered_values"] is None
    assert display["omitted"] is True
    assert display["item_count"] == ORDER_SELECTION_DISPLAY_LIMIT + 1
    assert display["limit"] == ORDER_SELECTION_DISPLAY_LIMIT
