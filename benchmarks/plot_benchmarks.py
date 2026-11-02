"""Gera gráficos SVG a partir da saída estruturada do benchmark."""

from __future__ import annotations

import argparse
import html
import json
import math
from collections.abc import Iterable
from pathlib import Path

ALGORITHM_FILES = {
    "inversões": "inversoes.svg",
    "seleção": "selecao.svg",
    "par mais próximo": "par-mais-proximo.svg",
}
THEORETICAL_COMPLEXITIES = {
    "inversões": ("O(n log n)", lambda n: n * math.log2(n)),
    "seleção": ("O(n)", lambda n: n),
    "par mais próximo": ("O(n log n)", lambda n: n * math.log2(n)),
}
WIDTH = 960
HEIGHT = 600
PLOT_LEFT = 82
PLOT_TOP = 116
PLOT_WIDTH = 820
PLOT_HEIGHT = 390


def _read_report(path: Path) -> dict[str, object]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"não foi possível ler o JSON: {error}") from error
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise SystemExit("JSON incompatível: schema_version deve ser 1")
    if not isinstance(report.get("environment"), dict):
        raise SystemExit("JSON inválido: environment ausente")
    if not isinstance(report.get("parameters"), dict):
        raise SystemExit("JSON inválido: parameters ausente")
    if not isinstance(report.get("measurements"), list):
        raise SystemExit("JSON inválido: measurements ausente")
    return report


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _points(measurements: Iterable[dict[str, object]]) -> list[tuple[int, float]]:
    return sorted(
        (int(item["size"]), float(item["median_ms"])) for item in measurements
    )


def _scale(value: float, maximum: float, start: float, length: float) -> float:
    return start + value / maximum * length if maximum else start


def _polyline(points: Iterable[tuple[float, float]], color: str, dashed: bool = False) -> str:
    coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    dash = ' stroke-dasharray="7 5"' if dashed else ""
    return (
        f'<polyline points="{coordinates}" fill="none" stroke="{color}" '
        f'stroke-width="3"{dash}/>'
    )


def _svg(
    algorithm: str,
    report: dict[str, object],
    series: dict[str, list[tuple[int, float]]],
) -> str:
    environment = report["environment"]
    parameters = report["parameters"]
    all_points = [point for values in series.values() for point in values]
    sizes = [size for size, _ in all_points]
    values = [value for _, value in all_points]
    min_size, max_size = min(sizes), max(sizes)
    max_value = max(values) * 1.12 or 1.0
    x = lambda size: _scale(size - min_size, max_size - min_size, PLOT_LEFT, PLOT_WIDTH)
    y = lambda value: PLOT_TOP + PLOT_HEIGHT - _scale(value, max_value, 0, PLOT_HEIGHT)
    colors = ["#1769aa", "#c2410c", "#15803d", "#7c3aed"]
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">',
        "<style>text{font-family:Arial,sans-serif;fill:#172033}.small{font-size:13px}"
        ".axis{stroke:#46566f;stroke-width:1}.grid{stroke:#dbe2ea;stroke-width:1}"
        ".legend{font-size:14px}</style>",
        f'<rect width="{WIDTH}" height="{HEIGHT}" fill="white"/>',
        f'<text x="{PLOT_LEFT}" y="34" font-size="24" font-weight="bold">'
        f"{_esc(algorithm)}: tempo por tamanho de entrada</text>",
        f'<text x="{PLOT_LEFT}" y="59" class="small">Mediana em ms; curvas teóricas normalizadas '
        "apenas para comparação visual</text>",
        f'<text x="{PLOT_LEFT}" y="81" class="small">Python: '
        f'{_esc(environment["python_implementation"])} {_esc(environment["python_version"])} | '
        f'Plataforma: {_esc(environment["platform"])} | CPUs lógicas: '
        f'{_esc(environment["cpu_count"])}</text>',
        f'<text x="{PLOT_LEFT}" y="99" class="small">Semente: {_esc(parameters["seed"])} | '
        f'Aquecimentos: {_esc(parameters["warmups"])} | Repetições: '
        f'{_esc(parameters["repeats"])} | quick: {_esc(parameters["quick"])}</text>',
    ]
    for tick in range(6):
        value = max_value * tick / 5
        y_position = y(value)
        lines.append(
            f'<line x1="{PLOT_LEFT}" y1="{y_position:.2f}" x2="{PLOT_LEFT + PLOT_WIDTH}" '
            f'y2="{y_position:.2f}" class="grid"/>'
        )
        lines.append(
            f'<text x="{PLOT_LEFT - 10}" y="{y_position + 5:.2f}" text-anchor="end" '
            f'class="small">{value:.2f}</text>'
        )
    for tick in range(6):
        size = min_size + (max_size - min_size) * tick / 5
        x_position = x(size)
        lines.append(
            f'<line x1="{x_position:.2f}" y1="{PLOT_TOP}" x2="{x_position:.2f}" '
            f'y2="{PLOT_TOP + PLOT_HEIGHT}" class="grid"/>'
        )
        lines.append(
            f'<text x="{x_position:.2f}" y="{PLOT_TOP + PLOT_HEIGHT + 24}" '
            f'text-anchor="middle" class="small">{size:.0f}</text>'
        )
    lines.extend(
        [
            f'<line x1="{PLOT_LEFT}" y1="{PLOT_TOP}" x2="{PLOT_LEFT}" '
            f'y2="{PLOT_TOP + PLOT_HEIGHT}" class="axis"/>',
            f'<line x1="{PLOT_LEFT}" y1="{PLOT_TOP + PLOT_HEIGHT}" '
            f'x2="{PLOT_LEFT + PLOT_WIDTH}" y2="{PLOT_TOP + PLOT_HEIGHT}" class="axis"/>',
            f'<text x="{PLOT_LEFT + PLOT_WIDTH / 2}" y="{HEIGHT - 26}" '
            'text-anchor="middle">tamanho da entrada (n)</text>',
            f'<text transform="translate(20 {PLOT_TOP + PLOT_HEIGHT / 2}) rotate(-90)" '
            'text-anchor="middle">tempo medido (ms)</text>',
        ]
    )
    for index, (implementation, points) in enumerate(series.items()):
        color = colors[index % len(colors)]
        lines.append(
            _polyline([(x(size), y(value)) for size, value in points], color)
        )
        for size, value in points:
            lines.append(
                f'<circle cx="{x(size):.2f}" cy="{y(value):.2f}" r="4" fill="{color}"/>'
            )
        legend_y = 140 + index * 24
        lines.append(
            f'<line x1="700" y1="{legend_y}" x2="728" y2="{legend_y}" '
            f'stroke="{color}" stroke-width="3"/>'
        )
        lines.append(
            f'<text x="738" y="{legend_y + 5}" class="legend">{_esc(implementation)}</text>'
        )
    complexity, formula = THEORETICAL_COMPLEXITIES[algorithm]
    primary = next(iter(series.values()))
    first_size, first_value = primary[0]
    base = formula(first_size)
    theoretical = [
        (size, first_value * formula(size) / base) for size in sorted(set(sizes))
    ]
    lines.append(
        _polyline([(x(size), y(value)) for size, value in theoretical], "#111827", True)
    )
    lines.append(
        '<line x1="700" y1="236" x2="728" y2="236" stroke="#111827" '
        'stroke-width="3" stroke-dasharray="7 5"/>'
    )
    lines.append(
        f'<text x="738" y="241" class="legend">curva teórica {complexity}</text>'
    )
    return "\n".join(lines + ["</svg>"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSON do benchmark")
    parser.add_argument("--output-dir", type=Path, required=True, help="diretório dos SVGs")
    arguments = parser.parse_args()
    report = _read_report(arguments.input)
    measurements = report["measurements"]
    grouped: dict[str, dict[str, list[tuple[int, float]]]] = {}
    for raw_measurement in measurements:
        if not isinstance(raw_measurement, dict):
            raise SystemExit("JSON inválido: medição não é um objeto")
        algorithm = raw_measurement.get("algorithm")
        implementation = raw_measurement.get("implementation")
        if algorithm not in ALGORITHM_FILES or not isinstance(implementation, str):
            raise SystemExit("JSON inválido: algoritmo ou implementação desconhecidos")
        grouped.setdefault(algorithm, {}).setdefault(implementation, []).append(
            (int(raw_measurement["size"]), float(raw_measurement["median_ms"]))
        )
    if set(grouped) != set(ALGORITHM_FILES):
        raise SystemExit("JSON incompleto: são esperados os três algoritmos centrais")
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    for algorithm, series in grouped.items():
        arguments.output_dir.joinpath(ALGORITHM_FILES[algorithm]).write_text(
            _svg(algorithm, report, series), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
