"""Interface de linha de comando do RankLab."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ranklab.algorithms import (
    AlgorithmTrace,
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
    trace_closest_pair,
    trace_ranking_comparison,
    trace_select_k,
    trace_select_percentile,
)
from ranklab.io.analysis_inputs import load_selection_values, load_weights
from ranklab.io.errors import RankLabError
from ranklab.io.readers import load_matrix, load_ranking
from ranklab.reporting import (
    load_audit_report,
    write_audit_report,
    write_standalone_html,
)
from ranklab.server import create_server
from ranklab.services import AuditReportRequest, generate_audit_report


def _port(value: str) -> int:
    """Valida a porta antes do bind, que falharia com ``OverflowError``."""

    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"porta inválida: {value!r}") from exc
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("a porta deve estar entre 0 e 65535")
    return port


def _print_trace(trace: AlgorithmTrace) -> None:
    """Imprime descrições estáveis sem alterar a saída quando o recurso está desligado."""

    print(f"Rastreamento ({trace.algorithm}):")
    if trace.steps is None:
        print(
            f"- omitido: {trace.reason} "
            f"({trace.item_count} itens; limite {trace.limit})"
        )
        return
    for index, step in enumerate(trace.steps, start=1):
        print(f"- passo {index} [{step.kind}]: {step.description}")


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
        "--trace", action="store_true", help="mostra os passos do merge sort"
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
    select_parser.add_argument(
        "--trace", action="store_true", help="mostra grupos, pivôs e partições"
    )

    closest_parser = subparsers.add_parser(
        "closest-pair",
        help="encontra o par de perfis mais próximo em dois critérios",
    )
    closest_parser.add_argument("path", metavar="MATRIZ", help="matriz JSON v1")
    closest_parser.add_argument("first_criterion", metavar="CRITERIO_X")
    closest_parser.add_argument("second_criterion", metavar="CRITERIO_Y")
    closest_parser.add_argument(
        "--trace", action="store_true", help="mostra divisões, deltas e faixas"
    )

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

    report_parser = subparsers.add_parser(
        "audit-report",
        help="gera um relatório JSON auditável com as quatro análises",
    )
    report_parser.add_argument("matrix_path", metavar="MATRIZ", help="matriz JSON v1")
    report_parser.add_argument(
        "--first-ranking", required=True, metavar="PRIMEIRO", help="primeiro ranking JSON v1"
    )
    report_parser.add_argument(
        "--trace",
        action="store_true",
        help="inclui no relatório o passo a passo dos três algoritmos",
    )
    report_parser.add_argument(
        "--second-ranking", required=True, metavar="SEGUNDO", help="segundo ranking JSON v1"
    )
    report_parser.add_argument(
        "--base-weights", required=True, metavar="PESOS_BASE", help="pesos do cenário base"
    )
    report_parser.add_argument(
        "--changed-weights",
        required=True,
        metavar="PESOS_ALTERADOS",
        help="pesos do cenário alterado",
    )
    report_parser.add_argument(
        "--closest-criteria",
        required=True,
        nargs=2,
        metavar=("CRITERIO_X", "CRITERIO_Y"),
        help="os dois critérios usados na proximidade",
    )
    selection_source = report_parser.add_mutually_exclusive_group(required=True)
    selection_source.add_argument(
        "--selection-values",
        metavar="VALORES",
        help="arquivo JSON contendo a lista para seleção",
    )
    selection_source.add_argument(
        "--selection-criterion",
        metavar="CRITERIO",
        help="critério da matriz cujos valores serão selecionados",
    )
    selection_order = report_parser.add_mutually_exclusive_group(required=True)
    selection_order.add_argument("--k", type=int, help="ordem 1-based para a seleção")
    selection_order.add_argument(
        "--percentile", type=float, help="percentil entre 0 e 100 para a seleção"
    )
    report_parser.add_argument(
        "--output",
        type=Path,
        metavar="RELATORIO",
        help="arquivo de saída; sem esta opção, imprime JSON no stdout",
    )
    report_parser.add_argument(
        "--html-output",
        type=Path,
        metavar="RELATORIO_HTML",
        help="gera também um visualizador HTML autocontido, abrível via file://",
    )

    serve_parser = subparsers.add_parser(
        "serve",
        help="abre o visualizador web do relatório auditável",
    )
    serve_parser.add_argument(
        "--report",
        type=Path,
        metavar="RELATORIO",
        help="relatório gerado por audit-report; sem esta opção, escolha-o no navegador",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="endereço de escuta (padrão: %(default)s, acessível só nesta máquina)",
    )
    serve_parser.add_argument(
        "--port",
        type=_port,
        default=8000,
        help="porta de escuta (padrão: %(default)s; 0 escolhe uma porta livre)",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.info:
        print(
            "RankLab 0.1.0 — carregamento, inversões, seleção determinística, "
            "par mais próximo, agregação e sensibilidade a pesos implementados."
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
            traced = trace_ranking_comparison(first, second) if args.trace else None
            result = traced.result if traced is not None else compare_rankings(first, second)
        except (RankLabError, RankingComparisonError) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1

        print(
            f"Rankings comparados: {first.ranking_id!r} x {second.ranking_id!r} "
            f"({result.item_count} itens)"
        )
        print(f"- Primeiro: {first.name!r} (origem: {first.origin!r})")
        print(f"- Segundo: {second.name!r} (origem: {second.origin!r})")
        second_positions = {item.item_id: item.position for item in second.items}
        print("Posições por item (variação positiva = subida no segundo ranking):")
        print("item_id | posição primeiro | posição segundo | variação | situação")
        for item in first.items:
            second_position = second_positions[item.item_id]
            delta = item.position - second_position
            situation = "inalterado" if delta == 0 else (
                "subiu" if delta > 0 else "caiu"
            )
            print(
                f"{item.item_id} | {item.position} | {second_position} | "
                f"{delta:+d} | {situation}"
            )
        print(
            "Quantidade de pares discordantes: "
            f"{result.discordant_pair_count} de {result.possible_pair_count}"
        )
        print(
            "Total de inversões (mesma medida de pares discordantes): "
            f"{result.discordant_pair_count}"
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
        if traced is not None:
            _print_trace(traced.trace)
        return 0

    if args.command == "select":
        try:
            values = load_selection_values(Path(args.path))
            if args.trace:
                traced = (
                    trace_select_k(values, args.k)
                    if args.k is not None
                    else trace_select_percentile(values, args.percentile)
                )
                result = traced.result
            else:
                traced = None
                result = (
                    select_k(values, args.k)
                    if args.k is not None
                    else select_percentile(values, args.percentile)
                )
        except SelectionError as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1
        if result.percentile is None:
            print(f"Elemento de ordem k={result.order}: {result.value!r}")
        else:
            print(
                f"Elemento do percentil {result.percentile:g}% "
                f"(k={result.order}): {result.value!r}"
            )
        if traced is not None:
            _print_trace(traced.trace)
        return 0

    if args.command == "closest-pair":
        try:
            matrix = load_matrix(Path(args.path))
            criteria = (args.first_criterion, args.second_criterion)
            traced = trace_closest_pair(matrix, criteria) if args.trace else None
            result = traced.result if traced is not None else closest_pair(matrix, criteria)
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
        if traced is not None:
            _print_trace(traced.trace)
        return 0

    if args.command == "aggregate-ranking":
        try:
            matrix = load_matrix(Path(args.path))
            weights = load_weights(Path(args.weights))
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
            base_weights = load_weights(Path(args.base_weights))
            changed_weights = load_weights(Path(args.changed_weights))
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

    if args.command == "audit-report":
        try:
            matrix_path = Path(args.matrix_path)
            first_ranking_path = Path(args.first_ranking)
            second_ranking_path = Path(args.second_ranking)
            base_weights_path = Path(args.base_weights)
            changed_weights_path = Path(args.changed_weights)
            matrix = load_matrix(matrix_path)
            first = load_ranking(first_ranking_path)
            second = load_ranking(second_ranking_path)
            base_weights = load_weights(base_weights_path)
            changed_weights = load_weights(changed_weights_path)
            selection_path = (
                Path(args.selection_values)
                if args.selection_values is not None
                else None
            )
            selection_values = (
                load_selection_values(selection_path)
                if selection_path is not None
                else None
            )
            report = generate_audit_report(
                AuditReportRequest(
                    matrix=matrix,
                    matrix_source=str(matrix_path),
                    first_ranking=first,
                    first_ranking_source=str(first_ranking_path),
                    second_ranking=second,
                    second_ranking_source=str(second_ranking_path),
                    base_weights=base_weights,
                    base_weights_source=str(base_weights_path),
                    changed_weights=changed_weights,
                    changed_weights_source=str(changed_weights_path),
                    closest_criteria=tuple(args.closest_criteria),
                    selection_criterion=args.selection_criterion,
                    selection_values=selection_values,
                    selection_values_source=(
                        str(selection_path) if selection_path is not None else None
                    ),
                    selection_order=args.k,
                    selection_percentile=args.percentile,
                    include_traces=args.trace,
                )
            )
            serialized = write_audit_report(report, args.output)
            if args.html_output is not None:
                write_standalone_html(report, args.html_output)
        except (
            OSError,
            RankLabError,
            RankingComparisonError,
            ClosestPairError,
            SelectionError,
            WeightedRankingError,
        ) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1
        if args.output is None:
            print(serialized, end="")
        else:
            print(f"Relatório auditável escrito em {args.output}")
        if args.html_output is not None:
            print(f"Visualizador HTML escrito em {args.html_output}")
        return 0

    if args.command == "serve":
        try:
            if args.report is not None:
                load_audit_report(args.report)
            server = create_server(args.report, args.host, args.port)
        except (OSError, RankLabError) as exc:
            print(f"Erro: {exc}", file=sys.stderr)
            return 1
        host, port = server.server_address[:2]
        print(f"Visualizador em http://{host}:{port}/ (Ctrl+C para encerrar)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0

    build_parser().print_help()
    return 0
