# Rastreamento dos algoritmos

O RankLab expõe o passo a passo de três algoritmos sem alterar seus contratos
principais. `compare_rankings`, `select_k`, `select_percentile` e
`closest_pair` continuam devolvendo somente seus resultados. As funções
`trace_ranking_comparison`, `trace_select_k`, `trace_select_percentile` e
`trace_closest_pair` devolvem o mesmo resultado acompanhado de um
`AlgorithmTrace`.

## Conteúdo

- **Merge sort:** divisões recursivas, folhas, combinações, inversões de cada
  combinação e total da subárvore.
- **Mediana das medianas:** grupos de até cinco, medianas, pivô, partições
  menor/igual/maior e partição seguida. Duplicatas permanecem visíveis.
- **Par mais próximo:** divisão por `x`, melhor par de cada lado, delta, faixa
  central e melhor par após a combinação.

Todo `TraceStep` contém `kind`, `depth`, `description` e `state`. A descrição
é adequada à leitura sem depender da visualização.

## CLI e interface

Use `--trace` em `compare-rankings`, `select`, `closest-pair` ou
`audit-report`. No navegador, marque “Incluir o passo a passo” antes de gerar o
relatório. Os controles Voltar, Avançar e Reproduzir são botões nativos; com
movimento reduzido, os passos mudam sem transições ou rolagem animada.

## Limite e complexidade

`TRACE_ITEM_LIMIT` vale 100. Entradas maiores ainda produzem o resultado, mas
o rastreamento é omitido. Quando desligado, não são materializados passos e as
complexidades assintóticas permanecem `O(n log n)` para inversões e par mais
próximo e `O(n)` no pior caso para a seleção determinística.
