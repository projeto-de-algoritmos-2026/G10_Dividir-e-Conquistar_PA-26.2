"""Interface de linha de comando do RankLab."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ranklab.algorithms import (
    PAIR_EXPLANATION_ITEM_LIMIT,
    ClosestPairError,
    RankingComparisonError,
    SelectionError,
    WeightedRankingError,
    aggregate_ranking,
    closest_pair,
    compare_rankings,
    compare_weight_scenarios,
    select_k,
    select_percentile,
)
from ranklab.io.errors import RankLabError
from ranklab.io.readers import load_matrix, load_ranking


def _load_weights(path: Path) -> dict[str, object]:
    """Lê um objeto JSON de pesos com erros apropriados para a CLI."""

    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise WeightedRankingError(f"{path}: arquivo não encontrado") from exc
    except UnicodeDecodeError as exc:
        raise WeightedRankingError(f"{path}: arquivo não é UTF-8 válido") from exc
    except OSError as exc:
        raise WeightedRankingError(f"{path}: não foi possível ler o arquivo: {exc}") from exc

    try:
        weights = json.loads(content)
    except json.JSONDecodeError as exc:
        raise WeightedRankingError(
            f"{path}: JSON inválido: {exc.msg} "
            f"(linha {exc.lineno}, coluna {exc.colno})"
        ) from exc

    if not isinstance(weights, dict):
        raise WeightedRankingError(
            f"{path}: o arquivo de pesos deve conter um objeto JSON"
        )
    return weights


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ranklab",
        description="Ferramenta acadêmica para análise auditável de rankings.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="mostra o estado atual do projeto",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMANDO")

    load_ranking_parser = subparsers.add_parser(
        "load-ranking",
        help="carrega e valida um arquivo de ranking JSON v1",
    )
    load_ranking_parser.add_argument(
        "path",
        metavar="ARQUIVO",
        help="caminho para o arquivo .json do ranking",
    )

    load_matrix_parser = subparsers.add_parser(
        "load-matrix",
        help="carrega e valida um arquivo de matriz de pontuação JSON v1",
    )
    load_matrix_parser.add_argument(
        "path",
        metavar="ARQUIVO",
        help="caminho para o arquivo .json da matriz",
    )

    compare_parser = subparsers.add_parser(
        "compare-rankings",
        help="compara dois rankings estritos pela distância de Kendall",
    )
    compare_parser.add_argument(
        "first_path",
        metavar="PRIMEIRO",
        help="caminho para o primeiro ranking JSON v1",
    )
    compare_parser.add_argument(
        "second_path",
        metavar="SEGUNDO",
        help="caminho para o segundo ranking JSON v1",
    )

    select_parser = subparsers.add_parser(
        "select",
        help="seleciona a ordem estatística de uma lista JSON sem ordená-la inteira",
    )
    select_parser.add_argument("path", metavar="ARQUIVO", help="arquivo JSON contendo uma lista")
    selection = select_parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--k", type=int, help="ordem 1-based")
    selection.add_argument("--percentile", type=float, help="percentil entre 0 e 100")

    closest_parser = subparsers.add_parser(
        "closest-pair",
        help="encontra o par de perfis mais próximo em dois critérios",
    )
    closest_parser.add_argument("path", metavar="MATRIZ", help="matriz JSON v1")
    closest_parser.add_argument("first_criterion", metavar="CRITERIO_X")
    closest_parser.add_argument("second_criterion", metavar="CRITERIO_Y")

    aggregate_parser = subparsers.add_parser(
        "aggregate-ranking",
        help="gera um ranking auditável por soma ponderada",
    )
    aggregate_parser.add_argument(
        "path",
        metavar="MATRIZ",
        help="matriz JSON v1",
    )
    aggregate_parser.add_argument(
        "--weights",
        required=True,
        metavar="PESOS",
        help="arquivo JSON que mapeia criterion_id para peso",
    )

    compare_weights_parser = subparsers.add_parser(
        "compare-weights",
        help="compara o ranking agregado sob duas configurações de pesos",
    )
    compare_weights_parser.add_argument(
        "path",
        metavar="MATRIZ",
        help="matriz JSON v1",
    )
    compare_weights_parser.add_argument(
        "--base-weights",
        required=True,
        metavar="PESOS_BASE",
        help="arquivo JSON com os pesos do cenário base",
    )
    compare_weights_parser.add_argument(
        "--changed-weights",
        required=True,
        metavar="PESOS_ALTERADOS",
        help="arquivo JSON com os pesos do cenário alterado",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.info:
        print(
            "RankLab 0.1.0 — IO, agregação e comparação de rankings e pesos "
            "implementados."
        )
        return 0

    if args.command == "load-ranking":
        try:
            ranking = load_ranking(Path(args.path))
        except RankLabError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1
        print(
            f"Ranking carregado: {ranking.ranking_id!r} "
            f"({len(ranking.items)} itens, origem: {ranking.origin!r})"
        )
        return 0

    if args.command == "load-matrix":
        try:
            matrix = load_matrix(Path(args.path))
        except RankLabError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1
        print(
            f"Matriz carregada: {matrix.matrix_id!r} "
            f"({len(matrix.criteria)} critérios, {len(matrix.items)} itens, "
            f"origem: {matrix.origin!r})"
        )
        return 0

    if args.command == "compare-rankings":
        try:
            first = load_ranking(Path(args.first_path))
            second = load_ranking(Path(args.second_path))
            result = compare_rankings(first, second)
        except (RankLabError, RankingComparisonError) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1

        print(
            f"Rankings comparados: {first.ranking_id!r} x {second.ranking_id!r} "
            f"({result.item_count} itens)"
        )
        print(
            "Quantidade de pares discordantes: "
            f"{result.discordant_pair_count} de {result.possible_pair_count}"
        )
        print(
            "Distância de Kendall normalizada: "
            f"{result.normalized_distance:.6f}"
        )

        if result.discordant_pairs is None:
            print(
                "Pares explicativos omitidos: "
                f"o limite é {PAIR_EXPLANATION_ITEM_LIMIT} itens."
            )
        elif not result.discordant_pairs:
            print("Pares discordantes: nenhum.")
        else:
            print("Pares discordantes:")
            for pair in result.discordant_pairs:
                print(
                    f"- {pair.earlier_in_first!r} antes de "
                    f"{pair.later_in_first!r} no primeiro; "
                    f"{pair.later_in_first!r} antes de "
                    f"{pair.earlier_in_first!r} no segundo"
                )
        return 0

    if args.command == "select":
        try:
            values = json.loads(Path(args.path).read_text(encoding="utf-8"))
            if not isinstance(values, list):
                raise SelectionError("o arquivo de seleção deve conter uma lista JSON")
            result = (
                select_k(values, args.k)
                if args.k is not None
                else select_percentile(values, args.percentile)
            )
        except (OSError, json.JSONDecodeError, SelectionError) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1
        if result.percentile is None:
            print(f"Elemento de ordem k={result.order}: {result.value!r}")
        else:
            print(
                f"Elemento do percentil {result.percentile:g}% "
                f"(k={result.order}): {result.value!r}"
            )
        return 0

    if args.command == "closest-pair":
        try:
            matrix = load_matrix(Path(args.path))
            result = closest_pair(
                matrix,
                (args.first_criterion, args.second_criterion),
            )
        except (RankLabError, ClosestPairError) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1
        print(
            f"Par mais próximo: {result.first_item_id!r} e {result.second_item_id!r}"
        )
        print(
            f"Critérios: {result.criterion_ids[0]!r}, {result.criterion_ids[1]!r}; "
            f"distância Euclidiana normalizada: {result.distance:.6f}"
        )
        return 0

    if args.command == "aggregate-ranking":
        try:
            matrix = load_matrix(Path(args.path))
            weights = _load_weights(Path(args.weights))
            result = aggregate_ranking(matrix, weights)
        except (
            RankLabError,
            WeightedRankingError,
        ) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1

        print(f"Ranking agregado da matriz {result.matrix_id!r}")
        print("Pesos (entrada -> normalizado):")
        for weight in result.weights:
            print(
                f"- {weight.criterion_id}: {weight.input_weight:.6f} -> "
                f"{weight.normalized_weight:.6f}"
            )

        criterion_ids = [criterion.criterion_id for criterion in matrix.criteria]
        print("Resultados:")
        print("posição | item_id | " + " | ".join((*criterion_ids, "score")))
        for item in result.items:
            normalized = " | ".join(
                f"{item.normalized_values[criterion_id]:.6f}"
                for criterion_id in criterion_ids
            )
            print(
                f"{item.position} | {item.item_id} | {normalized} | "
                f"{item.score:.6f}"
            )
        print(
            "Nota: os valores são arredondados apenas para exibição; "
            "a ordenação usa a precisão interna."
        )
        return 0

    if args.command == "compare-weights":
        try:
            matrix = load_matrix(Path(args.path))
            base_weights = _load_weights(Path(args.base_weights))
            changed_weights = _load_weights(Path(args.changed_weights))
            result = compare_weight_scenarios(
                matrix,
                base_weights,
                changed_weights,
            )
        except (
            RankLabError,
            RankingComparisonError,
            WeightedRankingError,
        ) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1

        print(f"Comparação de pesos da matriz {result.matrix_id!r}")
        print("Parâmetros compartilhados:")
        print(f"- normalização: {result.base_ranking.normalization}")
        print(f"- agregação: {result.base_ranking.aggregation}")
        print(f"- desempate: {result.base_ranking.tie_break}")
        directions = "; ".join(
            f"{criterion.criterion_id}={criterion.direction.value}"
            for criterion in matrix.criteria
        )
        print(f"- direções: {directions}")

        for label, ranking in (
            ("base", result.base_ranking),
            ("alterado", result.changed_ranking),
        ):
            print(f"Cenário {label} — pesos (entrada -> normalizado):")
            for weight in ranking.weights:
                print(
                    f"- {weight.criterion_id}: {weight.input_weight:.6f} -> "
                    f"{weight.normalized_weight:.6f}"
                )

        print("Comparação por item (variação de posição positiva = subida):")
        print(
            "item_id | posição base | posição alterada | variação posição | "
            "score base | score alterado | variação score | cruzamentos"
        )
        for item in result.items:
            if item.crossed_item_ids is None:
                crossings = (
                    "omitidos: limite de "
                    f"{PAIR_EXPLANATION_ITEM_LIMIT} itens excedido"
                )
            elif item.crossed_item_ids:
                crossings = ", ".join(item.crossed_item_ids)
            else:
                crossings = "-"
            print(
                f"{item.item_id} | {item.base_position} | "
                f"{item.changed_position} | {item.position_delta:+d} | "
                f"{item.base_score:.6f} | {item.changed_score:.6f} | "
                f"{item.score_delta:+.6f} | {crossings}"
            )

        comparison = result.ranking_comparison
        print(
            "Inversões: "
            f"{comparison.discordant_pair_count} de "
            f"{comparison.possible_pair_count}"
        )
        print(
            "Distância de Kendall normalizada: "
            f"{comparison.normalized_distance:.6f}"
        )
        print(
            "Nota: os valores são arredondados apenas para exibição; "
            "os cálculos usam a precisão interna."
        )
        return 0

    build_parser().print_help()
    return 0
