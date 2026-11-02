"""Cobertura do conjunto ampliado de demonstração e conferência com oráculos."""

from __future__ import annotations

import itertools
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ranklab.algorithms import (
    closest_pair,
    compare_rankings,
    compare_weight_scenarios,
    select_percentile,
    trace_closest_pair,
    trace_select_k,
)
from ranklab.domain.models import Direction, ScoringMatrix
from ranklab.io.analysis_inputs import load_weights
from ranklab.io.readers import load_matrix, load_ranking

REPOSITORY_ROOT = Path(__file__).parent.parent
LARGE = REPOSITORY_ROOT / "examples" / "large"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ranklab", *arguments],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )


def _quadratic_closest_pair(
    matrix: ScoringMatrix,
    criterion_ids: tuple[str, str],
) -> tuple[tuple[str, str], float]:
    criteria = {criterion.criterion_id: criterion for criterion in matrix.criteria}
    normalized_columns: dict[str, dict[str, float]] = {}
    for criterion_id in criterion_ids:
        values = [item.values[criterion_id] for item in matrix.items]
        minimum = min(values)
        maximum = max(values)
        normalized_columns[criterion_id] = {}
        for item in matrix.items:
            if maximum == minimum:
                normalized = 0.0
            else:
                normalized = (item.values[criterion_id] - minimum) / (maximum - minimum)
                if criteria[criterion_id].direction is Direction.LOWER_IS_BETTER:
                    normalized = 1.0 - normalized
            normalized_columns[criterion_id][item.item_id] = normalized

    candidates: list[tuple[float, tuple[str, str]]] = []
    for first, second in itertools.combinations(matrix.items, 2):
        distance = math.hypot(
            normalized_columns[criterion_ids[0]][first.item_id]
            - normalized_columns[criterion_ids[0]][second.item_id],
            normalized_columns[criterion_ids[1]][first.item_id]
            - normalized_columns[criterion_ids[1]][second.item_id],
        )
        candidates.append((distance, tuple(sorted((first.item_id, second.item_id)))))

    best_distance, best_pair = candidates[0]
    for distance, pair in candidates[1:]:
        tied = math.isclose(distance, best_distance, rel_tol=1e-12, abs_tol=1e-15)
        if (distance < best_distance and not tied) or (tied and pair < best_pair):
            best_distance, best_pair = distance, pair
    return best_pair, best_distance


def _quadratic_discordant_pairs(
    first_ids: list[str],
    second_ids: list[str],
) -> set[tuple[str, str]]:
    second_position = {item_id: index for index, item_id in enumerate(second_ids)}
    return {
        (first_ids[left], first_ids[right])
        for left in range(len(first_ids))
        for right in range(left + 1, len(first_ids))
        if second_position[first_ids[left]] > second_position[first_ids[right]]
    }


def test_large_demo_has_enough_items_for_recursion() -> None:
    reference = json.loads((LARGE / "reference.json").read_text(encoding="utf-8"))
    matrix = load_matrix(LARGE / "matriz.json")

    assert len(matrix.items) == 32
    assert reference["item_count"] == 32
    assert "não sustentam decisões reais" in matrix.origin

    closest_trace = trace_closest_pair(matrix, ("qualidade", "prazo_dias"))
    max_depth = max(step.depth for step in closest_trace.trace.steps)
    assert max_depth >= 3

    values = [item.values["qualidade"] for item in matrix.items]
    selection_trace = trace_select_k(values, 16)
    selection_depth = max(step.depth for step in selection_trace.trace.steps)
    assert selection_depth >= 2

    # O README justifica n=32 por estas profundidades; elas não podem divergir.
    assert max_depth == reference["reference"]["closest_trace_max_depth"]
    assert selection_depth == reference["reference"]["selection_trace_max_depth"]


def test_large_demo_is_reproducible_from_seed(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(LARGE / "generate_demo.py"),
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    assert result.returncode == 0, result.stderr

    generated = sorted(path.name for path in tmp_path.glob("*.json"))
    assert generated == sorted(path.name for path in LARGE.glob("*.json"))
    # Compara o JSON decodificado: o final de linha varia entre sistemas.
    for name in generated:
        assert json.loads((tmp_path / name).read_text(encoding="utf-8")) == json.loads(
            (LARGE / name).read_text(encoding="utf-8")
        ), name


def test_large_demo_matches_quadratic_oracles() -> None:
    matrix = load_matrix(LARGE / "matriz.json")
    first = load_ranking(LARGE / "ranking.json")
    second = load_ranking(LARGE / "ranking-operacional.json")
    reference = json.loads((LARGE / "reference.json").read_text(encoding="utf-8"))[
        "reference"
    ]

    comparison = compare_rankings(first, second)
    first_ids = [
        item.item_id for item in sorted(first.items, key=lambda item: item.position)
    ]
    second_ids = [
        item.item_id for item in sorted(second.items, key=lambda item: item.position)
    ]
    expected_pairs = _quadratic_discordant_pairs(first_ids, second_ids)
    assert comparison.discordant_pair_count == len(expected_pairs)
    assert comparison.discordant_pair_count == reference["discordant_pair_count"]

    pair = closest_pair(matrix, ("qualidade", "prazo_dias"))
    expected_pair, expected_distance = _quadratic_closest_pair(
        matrix, ("qualidade", "prazo_dias")
    )
    assert (pair.first_item_id, pair.second_item_id) == expected_pair
    assert pair.distance == pytest.approx(expected_distance)
    assert [pair.first_item_id, pair.second_item_id] == reference["closest_pair"]

    values = [item.values["qualidade"] for item in matrix.items]
    selection = select_percentile(values, 50)
    order = max(1, math.ceil(50 * len(values) / 100))
    assert selection.value == sorted(values)[order - 1]
    assert selection.value == reference["selection_percentile_50"]["value"]


def test_large_demo_weight_scenarios_change_and_stay() -> None:
    matrix = load_matrix(LARGE / "matriz.json")
    base = load_weights(LARGE / "pesos.json")
    muda = load_weights(LARGE / "pesos-alterados-muda.json")
    estavel = load_weights(LARGE / "pesos-alterados-estavel.json")

    sens_muda = compare_weight_scenarios(matrix, base, muda)
    sens_estavel = compare_weight_scenarios(matrix, base, estavel)

    assert sens_muda.ranking_comparison.discordant_pair_count > 0
    assert sens_estavel.ranking_comparison.discordant_pair_count == 0


def test_large_demo_end_to_end_audit_report(tmp_path: Path) -> None:
    output = tmp_path / "relatorio-large.json"
    result = _run(
        "audit-report",
        "examples/large/matriz.json",
        "--first-ranking",
        "examples/large/ranking.json",
        "--second-ranking",
        "examples/large/ranking-operacional.json",
        "--base-weights",
        "examples/large/pesos.json",
        "--changed-weights",
        "examples/large/pesos-alterados-muda.json",
        "--closest-criteria",
        "qualidade",
        "prazo_dias",
        "--selection-criterion",
        "qualidade",
        "--percentile",
        "50",
        "--output",
        str(output),
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert "não sustentam decisões reais" in report["matrix"]["origin"]
    assert report["analyses"]["ordering_divergence"]["discordant_pair_count"] == 246
    assert report["analyses"]["proximity"]["item_ids"] == [
        "fornecedor-01",
        "fornecedor-02",
    ]
    assert report["analyses"]["order_selection"]["value"] == pytest.approx(77.43)
    assert (
        report["analyses"]["weight_sensitivity"]["ranking_divergence"][
            "discordant_pair_count"
        ]
        == 164
    )


@pytest.mark.parametrize(
    ("arguments", "expected_fragment"),
    [
        (("load-matrix", "examples/large/matriz.json"), "Matriz carregada"),
        (
            (
                "compare-rankings",
                "examples/large/ranking.json",
                "examples/large/ranking-operacional.json",
            ),
            "Quantidade de pares discordantes: 246 de 496",
        ),
        (
            (
                "closest-pair",
                "examples/large/matriz.json",
                "qualidade",
                "prazo_dias",
            ),
            "'fornecedor-01' e 'fornecedor-02'",
        ),
        (
            ("select", "examples/large/valores-qualidade.json", "--percentile", "50"),
            "k=16): 77.43",
        ),
        (
            (
                "compare-weights",
                "examples/large/matriz.json",
                "--base-weights",
                "examples/large/pesos.json",
                "--changed-weights",
                "examples/large/pesos-alterados-muda.json",
            ),
            "Inversões: 164 de 496",
        ),
        (
            (
                "compare-weights",
                "examples/large/matriz.json",
                "--base-weights",
                "examples/large/pesos.json",
                "--changed-weights",
                "examples/large/pesos-alterados-estavel.json",
            ),
            "Inversões: 0 de 496",
        ),
    ],
)
def test_large_demo_documented_commands(
    arguments: tuple[str, ...],
    expected_fragment: str,
) -> None:
    result = _run(*arguments)
    assert result.returncode == 0, result.stderr
    assert expected_fragment in result.stdout
