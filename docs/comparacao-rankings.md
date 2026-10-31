# Comparação de rankings por inversões

O RankLab compara dois rankings completos e estritos dos mesmos itens. A
quantidade de pares discordantes é calculada por contagem de inversões com
merge sort, e a distância de Kendall normalizada expressa essa quantidade
como uma fração de todos os pares possíveis.

## Contrato e resultado

A API pública é `ranklab.algorithms.compare_rankings(first, second)`. Ambos os
argumentos devem ser objetos `Ranking` válidos e conter exatamente o mesmo
conjunto de `item_id`.

O resultado `RankingComparison` contém:

- `item_count`: número de itens comparados;
- `possible_pair_count`: total de pares, `n(n-1)/2`;
- `discordant_pair_count`: número de pares com ordem relativa diferente;
- `normalized_distance`: razão entre pares discordantes e possíveis;
- `discordant_pairs`: todos os pares discordantes para até 100 itens, ou
  `None` quando a explicação é omitida por tamanho.

Cada `DiscordantPair(earlier_in_first, later_in_first)` é orientado pelo
primeiro ranking: `earlier_in_first` aparece antes de `later_in_first` no
primeiro e depois dele no segundo. A ordem da coleção representa apenas a
ordem determinística em que o merge sort descobriu os pares.

O MVP não aceita rankings parciais nem empates. IDs duplicados, posições
duplicadas, posições que não formam exatamente `1..n`, rankings vazios e
conjuntos de itens diferentes são rejeitados. A ordem do array ou da tupla de
itens não define o ranking; somente o campo `position` é considerado.

## Transformação e contagem

Considere:

```text
primeiro: A, B, C, D
segundo:  B, A, D, C
```

As posições no segundo ranking são `B=1`, `A=2`, `D=3`, `C=4`. Ao percorrer o
primeiro ranking, obtém-se a sequência:

```text
[2, 1, 4, 3]
```

As inversões são `(2, 1)` e `(4, 3)`. Elas correspondem exatamente aos pares
de itens `(A, B)` e `(C, D)`, portanto a comparação resulta em 2 pares
discordantes entre 6 possíveis e distância `2/6 = 0,333333...`.

Uma inversão aparece quando um item `X` precede `Y` no primeiro ranking, mas a
posição de `X` no segundo é maior que a posição de `Y`. Isso é precisamente a
definição de um par cuja ordem relativa diverge.

## Argumento de corretude

O merge sort divide a sequência em duas metades. Por hipótese de indução, as
chamadas recursivas contam corretamente todas as inversões inteiramente
contidas em cada metade.

Durante o merge, as metades já estão ordenadas pelas posições do segundo
ranking. Quando o próximo elemento da metade direita é menor que o próximo da
esquerda, ele também é menor que todos os elementos ainda não consumidos da
esquerda. Há, portanto, exatamente `tamanho_esquerda - índice_esquerda`
inversões cruzadas, e cada uma é registrada uma vez. Quando o elemento da
esquerda é menor, nenhuma inversão cruzada nova é formada.

Assim, o merge conta todas e somente as inversões cruzadas. Somadas às
inversões internas contadas recursivamente, obtém-se exatamente o número de
pares discordantes da sequência inteira.

## Complexidade e normalização

Construir o mapa de posições custa `O(n)` tempo e espaço. A contagem por merge
sort custa `O(n log n)` tempo e usa um único buffer de `O(n)`, além da pilha
recursiva de `O(log n)`.

Para rankings com até 100 itens, materializar `k` pares explicativos adiciona
`Theta(k)` em tempo e espaço de saída. Esse custo é inevitável para retornar os
próprios pares e não integra o espaço auxiliar da contagem. O limite permite no
máximo `100 * 99 / 2 = 4.950` pares. Acima de 100 itens, a contagem e a
distância continuam disponíveis em `O(n log n)`, mas `discordant_pairs` é
`None`.

A distância normalizada é:

```text
discordant_pair_count / (n(n-1)/2)
```

Para `n < 2`, o denominador é zero e o RankLab adota a distância `0.0`, pois
não existe par possível que possa divergir. Como rankings vazios são inválidos
no formato v1, essa convenção é observável na aplicação para um ranking de um
item.

## Casos de referência

### Rankings iguais

```text
primeiro: A, B, C
segundo:  A, B, C
pares:    nenhum
contagem: 0 de 3
distância: 0.0
```

### Divergência parcial

```text
primeiro: A, B, C
segundo:  C, A, B
pares:    (A, C), (B, C)
contagem: 2 de 3
distância: 2/3
```

### Ordem reversa

```text
primeiro: A, B, C
segundo:  C, B, A
pares:    (A, B), (A, C), (B, C)
contagem: 3 de 3
distância: 1.0
```

## Uso pela linha de comando

```bash
ranklab compare-rankings primeiro.json segundo.json
```

A CLI mostra a contagem, o total possível e a distância com seis casas
decimais. Para entradas pequenas, também descreve cada inversão como “A antes
de B no primeiro; B antes de A no segundo”. Arquivos inválidos e rankings
incompatíveis produzem uma mensagem em `stderr` e código de saída `1`.
