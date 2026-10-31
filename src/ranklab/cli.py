"""Interface de linha de comando do RankLab."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ranklab.algorithms import (
    PAIR_EXPLANATION_ITEM_LIMIT,
    RankingComparisonError,
    compare_rankings,
)
from ranklab.io.errors import RankLabError
from ranklab.io.readers import load_matrix, load_ranking


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

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.info:
        print("RankLab 0.1.0 — IO, validação e comparação de rankings implementados.")
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

    build_parser().print_help()
    return 0
