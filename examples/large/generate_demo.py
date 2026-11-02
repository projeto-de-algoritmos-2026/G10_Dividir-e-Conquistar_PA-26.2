"""Gera o conjunto ampliado de demonstração com semente fixa.

Execute a partir da raiz do repositório, com o pacote instalado em modo
editável:

    python examples/large/generate_demo.py

A saída sobrescreve os JSON deste diretório, salvo se ``--output-dir`` indicar
outro; é assim que o teste confere a reprodução sem tocar nos arquivos versionados.
A semente e a justificação do tamanho estão documentadas em README.md.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from ranklab.algorithms import (
    closest_pair,
    compare_rankings,
    compare_weight_scenarios,
    select_percentile,
    trace_closest_pair,
    trace_select_k,
)
from ranklab.domain.models import (
    Criterion,
    Direction,
    MatrixItem,
    ScoringMatrix,
)
from ranklab.io.readers import load_matrix, load_ranking

ROOT = Path(__file__).resolve().parent
SEED = 20261102
ITEM_COUNT = 32
ORIGIN = (
    "Dados sintéticos gerados pelo Grupo RankLab com semente fixa 20261102; "
    "não representam empresas reais e não sustentam decisões reais de contratação."
)
RANKING_ORIGIN = (
    "Ranking sintético derivado da matriz ampliada (semente 20261102); "
    "não sustenta decisões reais."
)


def _build_items(rng: random.Random) -> list[dict[str, float | str]]:
    items: list[dict[str, float | str]] = []
    for index in range(1, ITEM_COUNT + 1):
        items.append(
            {
                "item_id": f"fornecedor-{index:02d}",
                "qualidade": round(rng.uniform(55, 98), 2),
                "prazo_dias": round(rng.uniform(5, 40), 2),
            }
        )
    # Par didático quase colado após a normalização min-max.
    items[0]["qualidade"] = 80.0
    items[0]["prazo_dias"] = 18.0
    items[1]["qualidade"] = 80.35
    items[1]["prazo_dias"] = 18.2
    return items


def _matrix(items_raw: list[dict[str, float | str]]) -> ScoringMatrix:
    return ScoringMatrix(
        matrix_id="fornecedores-2026-large-matriz",
        name="Pontuações ampliadas de fornecedores (demonstração)",
        origin=ORIGIN,
        criteria=(
            Criterion(
                "qualidade",
                "Qualidade técnica",
                Direction.HIGHER_IS_BETTER,
                "pontos",
            ),
            Criterion(
                "prazo_dias",
                "Prazo de entrega",
                Direction.LOWER_IS_BETTER,
                "dias",
            ),
        ),
        items=tuple(
            MatrixItem(
                item_id=str(row["item_id"]),
                values={
                    "qualidade": float(row["qualidade"]),
                    "prazo_dias": float(row["prazo_dias"]),
                },
            )
            for row in items_raw
        ),
    )


def _ranking_payload(
    ranking_id: str,
    name: str,
    ordered: list[dict[str, float | str]],
) -> dict[str, object]:
    return {
        "format_version": 1,
        "ranking_id": ranking_id,
        "name": name,
        "origin": RANKING_ORIGIN,
        "items": [
            {"item_id": row["item_id"], "position": position}
            for position, row in enumerate(ordered, start=1)
        ],
    }


def _write(output_dir: Path, name: str, payload: object) -> None:
    path = output_dir / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"escreveu {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    output_dir = parser.parse_args().output_dir

    rng = random.Random(SEED)
    items_raw = _build_items(rng)
    matrix = _matrix(items_raw)

    base_weights = {"qualidade": 3.0, "prazo_dias": 1.0}
    changed_muda = {"qualidade": 1.0, "prazo_dias": 4.0}
    # Pequeno reforço da qualidade que, nesta semente, não inverte a ordem.
    changed_estavel = {"qualidade": 3.05, "prazo_dias": 1.0}

    sens_muda = compare_weight_scenarios(matrix, base_weights, changed_muda)
    sens_estavel = compare_weight_scenarios(matrix, base_weights, changed_estavel)
    if sens_muda.ranking_comparison.discordant_pair_count <= 0:
        raise SystemExit("o cenário que deveria mudar a ordem não produziu inversões")
    if sens_estavel.ranking_comparison.discordant_pair_count != 0:
        raise SystemExit("o cenário estável produziu inversões inesperadas")

    tech_order = sorted(
        items_raw,
        key=lambda row: (-float(row["qualidade"]), str(row["item_id"])),
    )
    ops_order = sorted(
        items_raw,
        key=lambda row: (float(row["prazo_dias"]), str(row["item_id"])),
    )
    valores = [float(row["qualidade"]) for row in items_raw]

    _write(
        output_dir,
        "matriz.json",
        {
            "format_version": 1,
            "matrix_id": matrix.matrix_id,
            "name": matrix.name,
            "origin": matrix.origin,
            "criteria": [
                {
                    "criterion_id": criterion.criterion_id,
                    "name": criterion.name,
                    "direction": criterion.direction.value,
                    "unit": criterion.unit,
                }
                for criterion in matrix.criteria
            ],
            "items": [
                {
                    "item_id": row["item_id"],
                    "values": {
                        "qualidade": row["qualidade"],
                        "prazo_dias": row["prazo_dias"],
                    },
                }
                for row in items_raw
            ],
        },
    )
    _write(
        output_dir,
        "ranking.json",
        _ranking_payload(
            "fornecedores-2026-large-tecnico",
            "Avaliação técnica ampliada",
            tech_order,
        ),
    )
    _write(
        output_dir,
        "ranking-operacional.json",
        _ranking_payload(
            "fornecedores-2026-large-operacional",
            "Avaliação operacional ampliada",
            ops_order,
        ),
    )
    _write(output_dir, "valores-qualidade.json", valores)
    _write(output_dir, "pesos.json", base_weights)
    _write(output_dir, "pesos-alterados-muda.json", changed_muda)
    _write(output_dir, "pesos-alterados-estavel.json", changed_estavel)

    loaded = load_matrix(output_dir / "matriz.json")
    first = load_ranking(output_dir / "ranking.json")
    second = load_ranking(output_dir / "ranking-operacional.json")
    comparison = compare_rankings(first, second)
    pair = closest_pair(loaded, ("qualidade", "prazo_dias"))
    selection = select_percentile(valores, 50)
    expected_order = max(1, math.ceil(50 * len(valores) / 100))
    if selection.value != sorted(valores)[expected_order - 1]:
        raise SystemExit("seleção divergiu do oráculo ordenado")

    closest_trace = trace_closest_pair(loaded, ("qualidade", "prazo_dias"))
    closest_depth = max(step.depth for step in closest_trace.trace.steps)
    selection_trace = trace_select_k(list(valores), expected_order)
    selection_depth = max(step.depth for step in selection_trace.trace.steps)

    _write(
        output_dir,
        "reference.json",
        {
            "seed": SEED,
            "item_count": ITEM_COUNT,
            "generator": "examples/large/generate_demo.py",
            "justification": (
                "n=32: o caso-base do par mais próximo usa n<=3, produzindo "
                f"vários níveis de recursão (profundidade máxima observada "
                f"{closest_depth}); a mediana das medianas, em grupos de cinco, "
                f"também recorre (profundidade {selection_depth})."
            ),
            "reference": {
                "discordant_pair_count": comparison.discordant_pair_count,
                "possible_pair_count": comparison.possible_pair_count,
                "closest_pair": [pair.first_item_id, pair.second_item_id],
                "closest_distance": pair.distance,
                "selection_percentile_50": {
                    "value": selection.value,
                    "order": selection.order,
                },
                "weight_sensitivity_muda_discordant": (
                    sens_muda.ranking_comparison.discordant_pair_count
                ),
                "weight_sensitivity_estavel_discordant": (
                    sens_estavel.ranking_comparison.discordant_pair_count
                ),
                "closest_trace_max_depth": closest_depth,
                "selection_trace_max_depth": selection_depth,
            },
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
