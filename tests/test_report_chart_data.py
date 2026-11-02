"""Testes dos dados do relatório que alimentam os gráficos do visualizador."""

from __future__ import annotations

import itertools
import json
import math
import random
from pathlib import Path

import pytest

from ranklab.algorithms import closest_pair, project_profiles
from ranklab.cli import main
from ranklab.domain.models import Criterion, Direction, MatrixItem, ScoringMatrix
from ranklab.reporting import SELECTION_VALUE_LIMIT, write_audit_report

REPOSITORY_ROOT = Path(__file__).parent.parent
DEMO_REPORT_FIXTURE = REPOSITORY_ROOT / "tests" / "web" / "relatorio-demo.json"


def _write_matrix(path: Path, rows: list[tuple[str, float, float]]) -> Path:
    path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "matrix_id": "m",
                "name": "Matriz de teste",
                "origin": "teste",
                "criteria": [
                    {
                        "criterion_id": "x",
                        "name": "Eixo X",
                        "direction": "higher_is_better",
                        "unit": "u",
                    },
                    {
                        "criterion_id": "y",
                        "name": "Eixo Y",
                        "direction": "lower_is_better",
                        "unit": "u",
                    },
                ],
                "items": [
                    {"item_id": item_id, "values": {"x": x, "y": y}}
                    for item_id, x, y in rows
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    rows: list[tuple[str, float, float]],
    selection_values: list[float] | None = None,
) -> dict:
    matrix = _write_matrix(tmp_path / "matrix.json", rows)
    weights = tmp_path / "weights.json"
    weights.write_text('{"x": 1, "y": 1}', encoding="utf-8")
    source = ["--selection-criterion", "x"]
    if selection_values is not None:
        values = tmp_path / "values.json"
        values.write_text(json.dumps(selection_values), encoding="utf-8")
        source = ["--selection-values", str(values)]
    monkeypatch.setattr(
        "sys.argv",
        [
            "ranklab", "audit-report", str(matrix),
            "--first-ranking", "examples/ranking.json",
            "--second-ranking", "examples/ranking-operacional.json",
            "--base-weights", str(weights),
            "--changed-weights", str(weights),
            "--closest-criteria", "x", "y",
            *source, "--percentile", "50",
        ],
    )
    assert main() == 0
    return json.loads(capsys.readouterr().out)


def _random_rows(count: int) -> list[tuple[str, float, float]]:
    generator = random.Random(21)
    return [
        (f"item-{index:02d}", generator.uniform(0, 500), generator.uniform(-50, 50))
        for index in range(count)
    ]


def _coordinates(point: dict) -> tuple[float, float]:
    values = point["normalized_values"]
    return values["x"], values["y"]


def test_points_cover_every_item_in_matrix_order(tmp_path, monkeypatch, capsys) -> None:
    rows = _random_rows(30)

    points = _report(tmp_path, monkeypatch, capsys, rows)["analyses"]["proximity"]["points"]

    assert [point["item_id"] for point in points] == [row[0] for row in rows]
    assert all(
        point["source_values"] == {"x": x, "y": y}
        for point, (_, x, y) in zip(points, rows, strict=True)
    )


def test_point_coordinates_reproduce_reported_distance(
    tmp_path, monkeypatch, capsys
) -> None:
    proximity = _report(tmp_path, monkeypatch, capsys, _random_rows(30))["analyses"][
        "proximity"
    ]
    by_id = {point["item_id"]: point for point in proximity["points"]}
    first, second = (by_id[item_id] for item_id in proximity["item_ids"])

    assert math.dist(_coordinates(first), _coordinates(second)) == pytest.approx(
        proximity["distance"]
    )


def test_reported_distance_is_the_minimum_over_published_points(
    tmp_path, monkeypatch, capsys
) -> None:
    proximity = _report(tmp_path, monkeypatch, capsys, _random_rows(30))["analyses"][
        "proximity"
    ]

    minimum = min(
        math.dist(_coordinates(first), _coordinates(second))
        for first, second in itertools.combinations(proximity["points"], 2)
    )

    assert minimum == pytest.approx(proximity["distance"])


def test_points_respect_direction_and_constant_columns(
    tmp_path, monkeypatch, capsys
) -> None:
    rows = [("a", 5.0, 1.0), ("b", 5.0, 3.0)]

    points = _report(tmp_path, monkeypatch, capsys, rows)["analyses"]["proximity"]["points"]

    assert _coordinates(points[0]) == (0.0, 1.0)
    assert _coordinates(points[1]) == (0.0, 0.0)


def test_project_profiles_is_the_projection_behind_closest_pair() -> None:
    matrix = ScoringMatrix(
        matrix_id="m",
        name="teste",
        origin="teste",
        criteria=(
            Criterion("x", "X", Direction.HIGHER_IS_BETTER, "u"),
            Criterion("y", "Y", Direction.LOWER_IS_BETTER, "u"),
        ),
        items=tuple(
            MatrixItem(item_id, {"x": x, "y": y}) for item_id, x, y in _random_rows(12)
        ),
    )

    points = {point.item_id: point for point in project_profiles(matrix, ("x", "y"))}
    result = closest_pair(matrix, ("x", "y"))
    first, second = points[result.first_item_id], points[result.second_item_id]

    assert math.hypot(first.x - second.x, first.y - second.y) == pytest.approx(
        result.distance
    )


def test_collection_publishes_values_in_input_order(tmp_path, monkeypatch, capsys) -> None:
    report = _report(
        tmp_path, monkeypatch, capsys, _random_rows(3), selection_values=[9, 2, 7, 2]
    )

    collection = report["analyses"]["order_selection"]["collection"]

    assert collection["values"] == [9, 2, 7, 2]
    assert collection["item_count"] == 4


def test_collection_uses_matrix_column_for_criterion_source(
    tmp_path, monkeypatch, capsys
) -> None:
    rows = _random_rows(5)

    collection = _report(tmp_path, monkeypatch, capsys, rows)["analyses"][
        "order_selection"
    ]["collection"]

    assert collection["values"] == [row[1] for row in rows]


def test_collection_above_limit_is_flagged_as_omitted(
    tmp_path, monkeypatch, capsys
) -> None:
    values = list(range(SELECTION_VALUE_LIMIT + 1))

    selection = _report(
        tmp_path, monkeypatch, capsys, _random_rows(3), selection_values=values
    )["analyses"]["order_selection"]

    assert selection["collection"]["values"] is None
    assert selection["collection"]["item_count"] == len(values)
    assert "omitidos" in selection["collection"]["explanation"]
    assert selection["value"] == 500


def test_collection_at_limit_is_published(tmp_path, monkeypatch, capsys) -> None:
    values = list(range(SELECTION_VALUE_LIMIT))

    collection = _report(
        tmp_path, monkeypatch, capsys, _random_rows(3), selection_values=values
    )["analyses"]["order_selection"]["collection"]

    assert collection["values"] == values


def test_report_is_deterministic_for_same_inputs(tmp_path, monkeypatch, capsys) -> None:
    rows = _random_rows(10)

    first = _report(tmp_path, monkeypatch, capsys, rows)
    second = _report(tmp_path, monkeypatch, capsys, rows)

    assert write_audit_report(first, None) == write_audit_report(second, None)


def test_javascript_fixture_matches_generated_report(monkeypatch, capsys) -> None:
    monkeypatch.chdir(REPOSITORY_ROOT)
    monkeypatch.setattr(
        "sys.argv",
        [
            "ranklab", "audit-report", "examples/matriz.json",
            "--first-ranking", "examples/ranking.json",
            "--second-ranking", "examples/ranking-operacional.json",
            "--base-weights", "examples/pesos.json",
            "--changed-weights", "examples/pesos-alterados-muda.json",
            "--closest-criteria", "qualidade", "prazo_dias",
            "--selection-criterion", "qualidade", "--percentile", "50",
        ],
    )

    assert main() == 0
    generated = json.loads(capsys.readouterr().out)

    assert generated == json.loads(DEMO_REPORT_FIXTURE.read_text(encoding="utf-8"))
