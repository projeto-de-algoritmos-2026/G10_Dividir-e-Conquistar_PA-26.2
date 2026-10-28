"""Interface de linha de comando do RankLab."""

import argparse


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
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.info:
        print("RankLab 0.1.0 — fundação inicial; análises ainda não implementadas.")
    else:
        build_parser().print_help()
    return 0
