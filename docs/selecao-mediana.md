# Seleção determinística pela mediana das medianas

## Contrato

`select_k(items, k)` usa ordem estatística **1-based**: `k=1` é o menor
elemento e `k=len(items)` é o maior. Duplicatas permanecem na coleção e
ocupam posições próprias. A coleção não é alterada. `select_percentile`
aceita percentis no intervalo `[0, 100]` e usa a regra de posto mais próximo,
`k = max(1, ceil(percentil * n / 100))`; por isso o percentil 0 retorna o
menor elemento.

Coleções vazias, `k` fora de `1..n`, percentis fora do intervalo ou valores
não numéricos são rejeitados com `SelectionError`. O resultado informa o
elemento, a ordem e, quando aplicável, o percentil. Isso é uma seleção de
valor/elemento, não uma agregação ou um ranking combinado.

## Corretude e complexidade

A entrada é dividida em grupos de no máximo cinco. A mediana de cada grupo
forma uma coleção menor, e a mediana dessas medianas é usada como pivô.
Após o particionamento em valores menores, iguais e maiores, apenas a parte
que contém a ordem solicitada é recursivamente processada; o bloco de iguais
trata duplicatas sem risco de recursão infinita.

Pelo menos uma fração constante dos elementos fica de cada lado do pivô.
Assim, a recorrência é `T(n) <= T(n/5) + T(7n/10) + O(n)`, que resulta em
`O(n)` no pior caso, com `O(n)` espaço auxiliar. Apenas grupos de até cinco
são ordenados; a coleção inteira nunca é ordenada como atalho.
