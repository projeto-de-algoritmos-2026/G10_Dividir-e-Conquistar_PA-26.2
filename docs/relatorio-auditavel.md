# Relatório auditável

O comando `audit-report` reúne as quatro perguntas do MVP em um JSON
determinístico. As seções são independentes: divergência de ordenação,
proximidade em atributos, seleção de posição e sensibilidade aos pesos não são
misturadas nem tratadas como uma única medida de qualidade.

```bash
ranklab audit-report examples/matriz.json \
  --first-ranking primeiro.json \
  --second-ranking segundo.json \
  --base-weights examples/pesos.json \
  --changed-weights examples/pesos-alterados-muda.json \
  --closest-criteria qualidade prazo_dias \
  --selection-values valores.json \
  --k 2 \
  --output relatorio.json
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
- `median_position`: informa o arquivo de valores, a ordem ou percentil e o
  valor selecionado. Seleção de ordem não é posição em um ranking agregado.
- `weight_sensitivity`: preserva pesos de entrada e normalizados, valores
  normalizados, scores, posições, variações por item, cruzamentos e a
  divergência entre os cenários.

O objeto `inputs` guarda os caminhos usados para gerar o relatório e `matrix`
preserva a origem e os metadados dos critérios. Com os mesmos arquivos e
parâmetros, a saída é reproduzível; os números são calculados com a precisão
interna e apenas formatados pelo JSON.

## Limitações do MVP

O relatório aceita rankings estritos dos mesmos itens, seleção sobre uma lista
JSON e proximidade em exatamente dois atributos quantitativos. A proximidade
depende da normalização min-max orientada e da distância Euclidiana. Rankings
parciais, empates, dados ausentes e exportações diferentes de JSON não fazem
parte deste contrato.
