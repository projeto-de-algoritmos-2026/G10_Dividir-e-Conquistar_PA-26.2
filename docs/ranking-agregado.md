# Ranking agregado por soma ponderada

## Contrato e interpretação

`aggregate_ranking(matrix, weights)` recebe uma `ScoringMatrix` válida e um
mapeamento que associa exatamente um peso a cada `criterion_id`. O resultado é
um ranking estrito acompanhado dos valores normalizados, dos pesos de entrada,
dos pesos efetivamente usados e do score de cada item.

A soma ponderada é uma regra **compensatória**: um resultado alto em um
critério pode compensar um resultado baixo em outro. Portanto, pesos e
critérios devem representar a decisão pretendida; o algoritmo não descobre nem
valida preferências humanas.

## Normalização e direção de preferência

Para o item `i` e o critério `j`, sejam `x_ij` o valor original, `min_j` o
menor valor da coluna e `max_j` o maior. A normalização min-max orientada para
preferência produz valores entre `0` e `1`, em que `1` é sempre o melhor valor
observado:

- `higher_is_better`: `n_ij = (x_ij - min_j) / (max_j - min_j)`;
- `lower_is_better`: `n_ij = (max_j - x_ij) / (max_j - min_j)`.

Quando `max_j == min_j`, a coluna é constante e todos os seus valores
normalizados são `0`. Como ela não distingue alternativas, não acrescenta
score a nenhum item. Essa convenção também é usada pelo cálculo de par mais
próximo do RankLab.

A matriz v1 exige um número finito para cada critério de cada item. Valores
ausentes, `null`, booleanos, strings numéricas e números não finitos são
rejeitados; nenhum valor é imputado, convertido em zero ou descartado. A
agregação repete defensivamente essas verificações quando recebe um objeto de
domínio construído sem passar pelo leitor.

## Pesos e score

Os pesos de entrada podem estar em qualquer escala. Cada peso deve ser um
número finito não negativo, e pelo menos um deles deve ser positivo. Peso zero
é permitido e desativa a contribuição daquele critério. Pesos negativos,
booleanos, strings, `NaN`, infinitos, critérios ausentes e critérios
desconhecidos são erros.

Todo conjunto válido é normalizado para soma `1`:

```text
w'_j = w_j / sum(w)
```

Assim, pesos `[2, 1]`, `[20, 10]` e `[2/3, 1/3]` expressam a mesma preferência.
O score agregado do item `i` é:

```text
S_i = sum(w'_j * n_ij)
```

Como pesos e valores normalizados estão entre `0` e `1`, `S_i` também fica em
`[0, 1]`. O cálculo usa todos os valores internos, sem arredondamento
intermediário, e soma os critérios em ordem canônica de `criterion_id`. A ordem
do objeto JSON de pesos ou das linhas da matriz não muda o resultado.

## Ordenação, empate e precisão

Os itens são ordenados por score decrescente. Se dois scores internos forem
exatamente iguais, vence o `item_id` lexicograficamente menor. Esse desempate
produz posições estritas e reproduzíveis de `1` a `n`; ele é apenas técnico e
não significa que um dos itens empatados tenha desempenho substantivamente
melhor.

A API preserva os valores calculados. A CLI arredonda somente a apresentação
para seis casas decimais e informa que a ordenação usa o valor não arredondado.
Dois scores exibidos de forma igual podem, portanto, ter valores internos
diferentes e não constituir empate.

## Exemplo conferível manualmente

Considere um critério de benefício (`higher_is_better`) e um de custo
(`lower_is_better`):

| item | benefício bruto | custo bruto | benefício normalizado | custo normalizado |
| --- | ---: | ---: | ---: | ---: |
| `a` | 10 | 10 | 0.0 | 1.0 |
| `b` | 20 | 20 | 0.5 | 0.0 |
| `c` | 30 | 10 | 1.0 | 1.0 |

Com pesos de entrada `benefício=3` e `custo=1`, a soma é `4` e os pesos
efetivos são `0.75` e `0.25`. Logo:

```text
S_a = 0.75 * 0.0 + 0.25 * 1.0 = 0.25
S_b = 0.75 * 0.5 + 0.25 * 0.0 = 0.375
S_c = 0.75 * 1.0 + 0.25 * 1.0 = 1.0
```

O ranking resultante é `c`, `b`, `a`.

## Exemplo do repositório

O arquivo [`../examples/pesos.json`](../examples/pesos.json) atribui peso `2`
a `qualidade` e peso `1` a `prazo_dias`. Os pesos efetivos são `2/3` e `1/3`.
Aplicados a [`../examples/matriz.json`](../examples/matriz.json), produzem:

| posição | item | qualidade normalizada | prazo normalizado | score |
| ---: | --- | ---: | ---: | ---: |
| 1 | `fornecedor-a` | 1.000000 | 0.500000 | 0.833333 |
| 2 | `fornecedor-b` | 0.000000 | 1.000000 | 0.333333 |
| 3 | `fornecedor-c` | 0.444444 | 0.000000 | 0.296296 |

O cálculo pode ser reproduzido pela CLI:

```bash
ranklab aggregate-ranking examples/matriz.json --weights examples/pesos.json
```

O relatório mostra os pesos de entrada e normalizados antes da tabela do
ranking, além de um valor normalizado por critério e o score de cada item.
