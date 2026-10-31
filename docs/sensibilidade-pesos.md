# Comparação de cenários de pesos

O RankLab compara um cenário de pesos base com um cenário alterado sobre a
mesma matriz. Os dois rankings são recalculados pela soma ponderada e sua
divergência de ordem é medida pela contagem de inversões já usada na comparação
de rankings estritos.

## Contrato da API

A função pública é:

```python
compare_weight_scenarios(matrix, base_weights, changed_weights)
```

`matrix` é uma `ScoringMatrix`. Cada configuração de pesos deve mapear
exatamente todos os `criterion_id` da matriz para números finitos não negativos,
com ao menos um peso positivo. As duas configurações são validadas
independentemente pelas mesmas regras de `aggregate_ranking`.

O resultado `WeightScenarioComparison` contém:

- `base_ranking` e `changed_ranking`: resultados agregados completos, incluindo
  pesos informados e normalizados, valores normalizados, scores e posições;
- `items`: comparação por item na ordem do ranking base;
- `ranking_comparison`: contagem de inversões, total de pares, distância de
  Kendall normalizada e pares discordantes quando materializados.

Cada `ItemWeightChange` informa:

- posição e score nos dois cenários;
- `position_delta = base_position - changed_position`, portanto um valor
  positivo indica subida e um valor negativo indica queda;
- `score_delta = changed_score - base_score`;
- `crossed_item_ids`: itens cuja ordem relativa foi invertida.

Os cruzamentos são derivados dos pares discordantes. Para mais de 100 itens,
as listas são `None`, seguindo o limite do comparador de rankings; posições,
scores e contagem total de inversões continuam disponíveis.

## Regras preservadas

Os dois cenários usam exatamente a mesma matriz e, portanto, as mesmas:

- direções `higher_is_better` e `lower_is_better`;
- normalização min-max orientada pela direção;
- regra para colunas constantes;
- soma ponderada com pesos normalizados para soma 1;
- precisão interna sem arredondamento intermediário;
- política de desempate por score decrescente e `item_id` lexicográfico.

Assim, qualquer diferença de score ou posição decorre somente da configuração
de pesos. O arredondamento para seis casas ocorre apenas na CLI.

## Exemplo em que a ordem muda

A configuração base de [`../examples/pesos.json`](../examples/pesos.json) é:

```json
{"qualidade": 2, "prazo_dias": 1}
```

Ela gera a ordem `fornecedor-a`, `fornecedor-b`, `fornecedor-c`. Ao aplicar
[`../examples/pesos-alterados-muda.json`](../examples/pesos-alterados-muda.json):

```json
{"qualidade": 1, "prazo_dias": 3}
```

a ordem passa a ser `fornecedor-b`, `fornecedor-a`, `fornecedor-c`. Há uma
inversão: `fornecedor-a` e `fornecedor-b` cruzam de posição.

```bash
ranklab compare-weights examples/matriz.json \
  --base-weights examples/pesos.json \
  --changed-weights examples/pesos-alterados-muda.json
```

## Exemplo em que a ordem não muda

Com [`../examples/pesos-alterados-estavel.json`](../examples/pesos-alterados-estavel.json),
os pesos passam a `qualidade=3` e `prazo_dias=2`. Os scores mudam, mas a ordem
permanece `fornecedor-a`, `fornecedor-b`, `fornecedor-c`, com zero inversões.

```bash
ranklab compare-weights examples/matriz.json \
  --base-weights examples/pesos.json \
  --changed-weights examples/pesos-alterados-estavel.json
```

## Complexidade

Para `n` itens e `m` critérios, cada agregação calcula a normalização em
`O(nm)` e ordena os itens em `O(n log n)`. A comparação por inversões custa
`O(n log n)` e `O(n)` de espaço auxiliar. Logo, a comparação completa custa
`O(nm + n log n)` em tempo, desconsiderando a saída dos pares explicativos.

Para até 100 itens, materializar `k` inversões e associá-las aos itens adiciona
`Theta(k)` em tempo e espaço de saída. Acima desse limite, os pares não são
materializados e a contagem permanece `O(n log n)`.
