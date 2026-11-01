"""Benchmark reproduzível dos três algoritmos centrais e de seus oráculos.

Os tempos são evidência empírica, não testes de aceitação. Execute a partir da
raiz do repositório com ``python benchmarks/benchmark_algorithms.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import platform
import random
import statistics
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from ranklab.algorithms import closest_pair, compare_rankings, select_k  # noqa: E402
from ranklab.domain.models import (  # noqa: E402
    Criterion,
    Direction,
    MatrixItem,
    Ranking,
    RankingItem,
    ScoringMatrix,
)

SEED = 2026


@dataclass(frozen=True)
class Measurement:
    algorithm: str
    implementation: str
    size: int
    median_ms: float
    dataset_sha256: str


def _measure(operation: Callable[[], object], warmups: int, repeats: int) -> float:
    for _ in range(warmups):
        operation()
    samples: list[int] = []
    for _ in range(repeats):
        start = perf_counter_ns()
        operation()
        samples.append(perf_counter_ns() - start)
    return statistics.median(samples) / 1_000_000


def _fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def _ranking(ranking_id: str, ordered_ids: Sequence[str]) -> Ranking:
    return Ranking(
        ranking_id=ranking_id,
        name=ranking_id,
        origin="benchmark",
        items=tuple(
            RankingItem(item_id=item_id, position=position)
            for position, item_id in enumerate(ordered_ids, start=1)
        ),
    )


def _quadratic_inversion_count(first: Ranking, second: Ranking) -> int:
    first_ids = [
        item.item_id for item in sorted(first.items, key=lambda item: item.position)
    ]
    second_positions = {item.item_id: item.position for item in second.items}
    return sum(
        second_positions[first_ids[left]] > second_positions[first_ids[right]]
        for left in range(len(first_ids))
        for right in range(left + 1, len(first_ids))
    )


def _sorted_selection(items: Sequence[int], order: int) -> int:
    return sorted(items)[order - 1]


def _quadratic_closest_distance(matrix: ScoringMatrix) -> float:
    criterion_ids = ("x", "y")
    columns: dict[str, dict[str, float]] = {}
    for criterion_id in criterion_ids:
        values = [item.values[criterion_id] for item in matrix.items]
        minimum, maximum = min(values), max(values)
        columns[criterion_id] = {
            item.item_id: (
                0.0
                if maximum == minimum
                else (item.values[criterion_id] - minimum) / (maximum - minimum)
            )
            for item in matrix.items
        }

    return min(
        math.hypot(
            columns["x"][first.item_id] - columns["x"][second.item_id],
            columns["y"][first.item_id] - columns["y"][second.item_id],
        )
        for first, second in itertools.combinations(matrix.items, 2)
    )


def _matrix(points: Sequence[tuple[str, float, float]]) -> ScoringMatrix:
    return ScoringMatrix(
        matrix_id="benchmark",
        name="benchmark",
        origin="benchmark",
        criteria=(
            Criterion("x", "X", Direction.HIGHER_IS_BETTER, "u"),
            Criterion("y", "Y", Direction.HIGHER_IS_BETTER, "u"),
        ),
        items=tuple(
            MatrixItem(item_id=item_id, values={"x": x, "y": y})
            for item_id, x, y in points
        ),
    )


def _record(
    measurements: list[Measurement],
    *,
    algorithm: str,
    implementation: str,
    size: int,
    dataset: object,
    operation: Callable[[], object],
    warmups: int,
    repeats: int,
) -> None:
    measurements.append(
        Measurement(
            algorithm=algorithm,
            implementation=implementation,
            size=size,
            median_ms=_measure(operation, warmups, repeats),
            dataset_sha256=_fingerprint(dataset),
        )
    )


def run_benchmarks(warmups: int, repeats: int, quick: bool) -> list[Measurement]:
    measurements: list[Measurement] = []
    inversion_sizes = (128, 256) if quick else (128, 256, 512, 1024, 2048, 4096)
    selection_sizes = (128, 256) if quick else (128, 256, 512, 1024, 2048, 4096, 8192)
    closest_sizes = (64, 128) if quick else (64, 128, 256, 512, 1024, 2048)

    for size in inversion_sizes:
        generator = random.Random(SEED + size)
        first_ids = [f"item-{index:05d}" for index in range(size)]
        second_ids = first_ids.copy()
        generator.shuffle(first_ids)
        generator.shuffle(second_ids)
        first = _ranking("first", first_ids)
        second = _ranking("second", second_ids)
        dataset = {"first": first_ids, "second": second_ids}
        _record(
            measurements,
            algorithm="inversões",
            implementation="dividir-e-conquistar",
            size=size,
            dataset=dataset,
            operation=lambda: compare_rankings(first, second),
            warmups=warmups,
            repeats=repeats,
        )
        if size <= 512:
            _record(
                measurements,
                algorithm="inversões",
                implementation="oráculo quadrático",
                size=size,
                dataset=dataset,
                operation=lambda: _quadratic_inversion_count(first, second),
                warmups=warmups,
                repeats=repeats,
            )

    for size in selection_sizes:
        generator = random.Random(SEED * 2 + size)
        values = [generator.randint(-size, size) for _ in range(size)]
        order = size // 2 + 1
        dataset = {"values": values, "order": order}
        _record(
            measurements,
            algorithm="seleção",
            implementation="mediana-das-medianas",
            size=size,
            dataset=dataset,
            operation=lambda: select_k(values, order),
            warmups=warmups,
            repeats=repeats,
        )
        _record(
            measurements,
            algorithm="seleção",
            implementation="oráculo por ordenação",
            size=size,
            dataset=dataset,
            operation=lambda: _sorted_selection(values, order),
            warmups=warmups,
            repeats=repeats,
        )

    for size in closest_sizes:
        generator = random.Random(SEED * 3 + size)
        points = [
            (
                f"item-{index:05d}",
                generator.uniform(-1_000_000, 1_000_000),
                generator.uniform(-1_000_000, 1_000_000),
            )
            for index in range(size)
        ]
        matrix = _matrix(points)
        dataset = {"points": points}
        _record(
            measurements,
            algorithm="par mais próximo",
            implementation="dividir-e-conquistar",
            size=size,
            dataset=dataset,
            operation=lambda: closest_pair(matrix, ("x", "y")),
            warmups=warmups,
            repeats=repeats,
        )
        if size <= 512:
            _record(
                measurements,
                algorithm="par mais próximo",
                implementation="oráculo quadrático",
                size=size,
                dataset=dataset,
                operation=lambda: _quadratic_closest_distance(matrix),
                warmups=warmups,
                repeats=repeats,
            )

    return measurements


def _print_report(
    measurements: Sequence[Measurement], warmups: int, repeats: int
) -> None:
    print("# Benchmark dos algoritmos RankLab")
    print()
    print(f"- Python: {platform.python_implementation()} {platform.python_version()}")
    print(f"- Plataforma: {platform.platform()}")
    print(f"- CPUs lógicas: {os.cpu_count()}")
    print(f"- Semente: {SEED}")
    print(f"- Aquecimentos: {warmups}")
    print(f"- Repetições medidas: {repeats}")
    print()
    print("| Algoritmo | Implementação | n | Mediana (ms) | Dados SHA-256 |")
    print("| --- | --- | ---: | ---: | --- |")
    for result in measurements:
        print(
            f"| {result.algorithm} | {result.implementation} | {result.size} "
            f"| {result.median_ms:.6f} | `{result.dataset_sha256}` |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="usa apenas dois tamanhos por algoritmo para uma verificação rápida",
    )
    arguments = parser.parse_args()
    if arguments.warmups < 0:
        parser.error("--warmups deve ser não negativo")
    if arguments.repeats < 1:
        parser.error("--repeats deve ser positivo")

    measurements = run_benchmarks(
        warmups=arguments.warmups,
        repeats=arguments.repeats,
        quick=arguments.quick,
    )
    _print_report(measurements, arguments.warmups, arguments.repeats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
