# Contratos de dados — versão 1

Este documento define os formatos mínimos de entrada do RankLab. Os arquivos
são JSON UTF-8, usam a extensão `.json` e declaram `format_version: 1`. Os
exemplos completos estão em `examples/ranking.json`,
`examples/ranking-operacional.json` e `examples/matriz.json`; sua origem e
licença estão documentadas em `examples/README.md`.

## Identificadores compartilhados

`item_id` é uma string obrigatória, estável e única para cada entidade. Use o mesmo identificador em rankings e matrizes para que as análises possam ser combinadas. IDs são comparados exatamente como escritos: diferenças de maiúsculas, espaços ou acentos representam IDs diferentes. Não use o nome de exibição como chave. `ranking_id` e `matrix_id` identificam cada conjunto de entrada; `criterion_id` identifica uma coluna dentro da matriz.

Nomes são rótulos para apresentação e não precisam ser únicos. `origin` deve descrever a procedência dos dados (por exemplo, "exemplo fictício"); não é uma URL obrigatória.

## Ranking estrito

Formato de topo: `format_version`, `ranking_id`, `name`, `origin` e `items`. Cada item contém `item_id` e `position`, uma posição inteira de 1 até `n`.

O ranking v1 é completo e estrito: cada item aparece uma vez e cada posição aparece uma vez, sem lacunas. Empates não são aceitos; a fonte deve fornecer um desempate explícito e reproduzível antes da importação. Um item ausente torna o ranking incompatível com uma comparação completa. Ao comparar dois rankings, ambos devem conter exatamente o mesmo conjunto de `item_id`.

O array `items` pode vir em qualquer ordem; a ordem é determinada por `position`. Valores de posição não são arredondados nem convertidos implicitamente.

## Matriz de pontuação

Formato de topo: `format_version`, `matrix_id`, `name`, `origin`, `criteria` e `items`.

Cada critério exige `criterion_id`, `name`, `direction` e `unit`. `direction` é `higher_is_better` quando valores maiores são preferidos, ou `lower_is_better` quando valores menores são preferidos. `unit` é uma string, como `"pontos"`, `"ms"` ou `"kg"`; use `"adimensional"` para medidas sem unidade.

Cada linha exige `item_id` e `values`, um objeto que associa cada `criterion_id` a um número JSON. Na versão 1, todas as linhas devem fornecer exatamente os critérios declarados, e cada critério deve ter um identificador único. Valores ausentes, `null`, strings numéricas, booleanos e números não finitos (`NaN`, `Infinity`, `-Infinity`, que não são números JSON válidos) são rejeitados. Valores zero e negativos são permitidos. A unidade e a escala de origem são informativas; a normalização pertence à etapa de análise e deve ser documentada por ela.

Os IDs de itens da matriz não precisam coincidir com os de um ranking isolado, mas uma análise que combine as entradas exige IDs correspondentes conforme o conjunto de itens esperado. Itens duplicados na matriz são inválidos.

## Precisão e erros

O formato preserva os valores numéricos fornecidos, sem arredondamento definido pelo contrato. Relatórios podem arredondar apenas para exibição, informando a precisão usada; cálculos não devem alterar silenciosamente os dados de origem.

Leitores devem rejeitar o arquivo com mensagem que identifique arquivo, caminho do campo e motivo, por exemplo: `matriz.json: items[1].values.custo: valor ausente`. A validação deve também apontar IDs duplicados, posições inválidas e critérios desconhecidos. Nenhuma política converte entrada inválida em zero ou descarta linhas silenciosamente.

## Exemplo de ranking

```json
{
  "format_version": 1,
  "ranking_id": "fornecedores-2026-a",
  "name": "Avaliação técnica",
  "origin": "exemplo fictício",
  "items": [
    {"item_id": "fornecedor-a", "position": 1},
    {"item_id": "fornecedor-b", "position": 2},
    {"item_id": "fornecedor-c", "position": 3}
  ]
}
```

## Exemplo de matriz

```json
{
  "format_version": 1,
  "matrix_id": "fornecedores-2026-matriz",
  "name": "Pontuações dos fornecedores",
  "origin": "exemplo fictício",
  "criteria": [
    {
      "criterion_id": "qualidade",
      "name": "Qualidade técnica",
      "direction": "higher_is_better",
      "unit": "pontos"
    },
    {
      "criterion_id": "prazo_dias",
      "name": "Prazo de entrega",
      "direction": "lower_is_better",
      "unit": "dias"
    }
  ],
  "items": [
    {
      "item_id": "fornecedor-a",
      "values": {"qualidade": 92.5, "prazo_dias": 12}
    },
    {
      "item_id": "fornecedor-b",
      "values": {"qualidade": 88, "prazo_dias": 9}
    },
    {
      "item_id": "fornecedor-c",
      "values": {"qualidade": 90, "prazo_dias": 15}
    }
  ]
}
```
