# Relatório auditável

O comando `audit-report` reúne as quatro perguntas do MVP em um JSON
determinístico de formato `ranklab-audit-report`, versão 2. As seções são
independentes: divergência de ordenação, proximidade em atributos, seleção de
ordem e sensibilidade aos pesos não são misturadas nem tratadas como uma única
medida de qualidade.

```bash
python -m ranklab audit-report examples/matriz.json --first-ranking examples/ranking.json --second-ranking examples/ranking-operacional.json --base-weights examples/pesos.json --changed-weights examples/pesos-alterados-muda.json --closest-criteria qualidade prazo_dias --selection-criterion qualidade --percentile 50 --output relatorio.json
```

Sem `--output`, o JSON é emitido no `stdout`. Entradas inválidas produzem erro
no `stderr` e código de saída `1`; nunca são convertidas em uma seção vazia.

## Seções e perguntas respondidas

- `ordering_divergence`: identifica os rankings por nome e origem, lista a
  posição de cada item nos dois lados, calcula o total bruto de pares
  discordantes/inversões e a distância de Kendall normalizada. Pares
  explicativos são listados quando o limite do comparador permite.
- `proximity`: registra os dois critérios, direção, unidade, valores de origem,
  normalização, métrica e distância do par mais próximo. A interpretação
  explicita que a proximidade não é similaridade geral.
- `order_selection`: informa a origem dos valores, quantidade, ordem ou
  percentil e valor selecionado. Com `--selection-criterion`, nome, unidade e
  ID do critério tornam o resultado interpretável. Seleção de ordem não é
  posição em um ranking agregado.
- `weight_sensitivity`: preserva pesos de entrada e normalizados, valores
  normalizados, scores, posições, variações por item, cruzamentos e a
  divergência entre os cenários.

O objeto `inputs` guarda os caminhos e a fonte de seleção usados para gerar o
relatório, e `matrix` preserva a origem e os metadados dos critérios. Com os
mesmos arquivos e parâmetros, a saída é reproduzível; os números são
calculados com a precisão interna e apenas formatados pelo JSON.

Para selecionar uma coleção externa em vez de uma coluna da matriz, substitua
`--selection-criterion qualidade` por
`--selection-values examples/valores-qualidade.json`. As duas opções são
mutuamente exclusivas.

## Migração do formato 1 para o 2

A versão 2 renomeia a seção `median_position` para `order_selection`. O nome
anterior era impreciso porque a API aceita qualquer ordem `k` ou percentil,
não apenas a mediana. A fonte da seleção passou a ser um objeto estruturado e
pode identificar um arquivo JSON ou um critério da matriz. Os contratos dos
arquivos de ranking e matriz continuam na versão 1 e não foram alterados.

## Limitações do MVP

O relatório aceita rankings estritos dos mesmos itens, seleção sobre uma lista
JSON ou coluna quantitativa da matriz e proximidade em exatamente dois
atributos. A proximidade depende da normalização min-max orientada e da
distância Euclidiana. Rankings parciais, empates, dados ausentes, critérios
categóricos e exportações diferentes de JSON não fazem parte deste contrato.
A soma ponderada é compensatória, a normalização min-max é sensível aos
extremos e os dados fictícios não sustentam decisões reais.
