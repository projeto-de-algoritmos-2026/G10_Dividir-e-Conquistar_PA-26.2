# Corretude e desempenho dos algoritmos centrais

Este relatório reúne as evidências dos algoritmos de contagem de inversões,
seleção determinística e par mais próximo. A prova de corretude, que vale para
toda entrada que satisfaz o contrato, é apresentada separadamente da avaliação
empírica, que observa apenas execuções particulares.

## Contratos e invariantes

### Contagem de inversões

`compare_rankings(first, second)` recebe dois rankings estritos, não vazios,
com posições `1..n`, IDs únicos e exatamente o mesmo conjunto de itens. A
ordem física das tuplas não é significativa; os itens são primeiro ordenados
por `position`.

Ao percorrer o primeiro ranking, cada ID é substituído por sua posição no
segundo. Como ambos contêm os mesmos IDs uma única vez, a sequência resultante
é uma permutação de `1..n`. Para quaisquer itens `X` e `Y`, com `X` anterior a
`Y` no primeiro ranking, a sequência contém uma inversão exatamente quando a
posição de `X` no segundo é maior que a de `Y`. Logo, há uma bijeção entre as
inversões da sequência e os pares discordantes dos rankings.

Em `_sort_and_count`, o invariante de cada chamada sobre `[start:end)` é:

1. ao retornar, o trecho está ordenado pela posição no segundo ranking;
2. o valor retornado é o número exato de inversões que existiam no trecho;
3. quando solicitada, cada inversão é materializada uma única vez e orientada
   pela ordem do primeiro ranking.

### Seleção determinística

`select_k(items, k)` usa ordem estatística iniciada em 1, aceita duplicatas e
não altera a coleção recebida. Internamente, o alvo é convertido para índice
iniciado em zero. `select_percentile` aceita `[0, 100]` e usa
`max(1, ceil(p*n/100))`.

Para um pivô, o particionamento forma três coleções disjuntas — menores,
iguais e maiores — cuja união preserva todos os elementos da chamada. O alvo
pertence a exatamente uma dessas faixas. Se estiver na faixa de iguais,
qualquer elemento dela tem a chave de ordem correta; caso contrário, o índice
é preservado na faixa inferior ou ajustado pelo tamanho das faixas descartadas
antes da recursão.

### Par mais próximo

`closest_pair(matrix, (x, y))` exige ao menos dois itens e exatamente dois
critérios distintos existentes. Valores precisam ser números finitos. Cada
eixo é normalizado por min-max; colunas constantes são projetadas em zero e a
direção `lower_is_better` reflete o eixo. Reflexão e a convenção de coluna
constante mantêm a interpretação documentada de proximidade após a
normalização.

Em `_closest`, `by_x` e `by_y` contêm os mesmos pontos, respectivamente
ordenados por `x` e por `y`. A divisão preserva essa correspondência nas duas
metades. O melhor resultado acumulado é sempre o menor pela distância; em
distâncias numericamente empatadas, vence o par de IDs lexicograficamente
menor.

## Argumentos de corretude

### Contagem de inversões por merge sort

O caso base, com zero ou um elemento, já está ordenado e não contém inversão.
Por hipótese de indução, as duas chamadas recursivas ordenam suas metades e
contam corretamente todas as inversões internas.

Durante o merge, se o próximo elemento da esquerda é menor, ele não forma
inversão cruzada com nenhum elemento restante da direita. Se o próximo da
direita é menor, ele é menor que todos os elementos ainda não consumidos da
esquerda, pois essa metade está ordenada. Assim, há exatamente
`middle - left` novas inversões. Cada inversão interna ou cruzada pertence a
uma única dessas categorias e é contada uma vez. Pelo invariante e pela
bijeção descrita acima, o resultado é exatamente o número de pares
discordantes.

### Seleção pela mediana das medianas

O caso base ordena no máximo cinco elementos e devolve diretamente o alvo.
Nos demais casos, a mediana das medianas fornece um pivô pertencente à
coleção. O invariante da partição garante que descartar duas das três faixas
não descarta o elemento de ordem procurado. A chamada recursiva recebe o mesmo
problema em uma coleção estritamente menor, ou retorna na faixa de iguais;
portanto termina e devolve uma chave com exatamente a ordem solicitada.

Ao agrupar de cinco em cinco, pelo menos metade das medianas é maior ou igual
ao pivô e cada uma dessas medianas garante elementos do seu grupo desse lado;
o argumento simétrico vale para o lado menor. Desconsiderando um grupo
incompleto e o grupo do pivô, no máximo `7n/10 + O(1)` elementos seguem para a
recursão principal. Duplicatas são reunidas na faixa de iguais, evitando
recursão sem progresso.

### Par mais próximo por divisão e conquista

O caso base enumera todos os pares de até três pontos. Para mais pontos, todo
par possível está inteiramente na metade esquerda, inteiramente na direita ou
cruza a linha de divisão. Por hipótese de indução, as duas primeiras
categorias são resolvidas corretamente.

Se um par cruzado puder melhorar a distância `d` já encontrada nas metades,
seus dois pontos precisam estar a no máximo `d` da divisão e, portanto,
pertencem à faixa central. Na faixa ordenada por `y`, o argumento geométrico
de empacotamento mostra que basta comparar cada ponto com os sete sucessores.
Assim, nenhum par cruzado capaz de melhorar o resultado é omitido. A escolha
entre esquerda, direita e faixa, incluindo o desempate, devolve o par
globalmente mais próximo.

## Complexidade de tempo e espaço

| Algoritmo | Tempo | Espaço auxiliar | Observações |
| --- | --- | --- | --- |
| Inversões | `O(n log n)` | `O(n)` | Mapa e buffer são lineares; a pilha tem `O(log n)`. Materializar `k` pares adiciona `Theta(k)` em tempo e saída. |
| Seleção | `O(n)` no pior caso | `O(n)` | `T(n) <= T(n/5) + T(7n/10 + O(1)) + O(n)`; listas de partição e medianas somam espaço linear no pico. |
| Par mais próximo | `O(n log n)` | `O(n)` | Ordenações iniciais dominam; cada nível filtra e percorre os pontos linearmente. |

Na comparação de rankings, os pares explicativos são materializados somente
até 100 itens, no máximo 4.950 pares. Acima desse limite, a contagem mantém o
custo `O(n log n)` e `discordant_pairs` é `None`.

Os oráculos dos testes deliberadamente priorizam simplicidade e independência:
inversões e par mais próximo usam `O(n²)`; seleção usa ordenação `O(n log n)`.

## Evidências automatizadas

Os testes usam casos manuais, limites, entradas inválidas, padrões ordenados,
reversos, alternados, duplicados, constantes e conjuntos pseudoaleatórios com
semente fixa. Para entradas pequenas, os resultados são comparados com
oráculos que não chamam funções internas das implementações:

- inversões: todos os pares são examinados diretamente;
- seleção: o elemento esperado é obtido por ordenação completa;
- par mais próximo: normalização independente seguida da enumeração de todos
  os pares.

O comando focado executa 86 testes:

```bash
python -m pytest -q -p no:cacheprovider tests/test_ranking_comparison.py tests/test_deterministic_selection.py tests/test_closest_pair.py
```

Esses testes aumentam a confiança e detectam regressões, mas não substituem os
argumentos para entradas arbitrárias.

## Avaliação empírica

### Metodologia

O script `benchmarks/benchmark_algorithms.py` usa somente a biblioteca padrão,
`random.Random(2026)`, um aquecimento, cinco repetições e a mediana de
`perf_counter_ns`. Os dados são construídos antes da região medida. O hash em
cada linha identifica o conteúdo da entrada; implementação e oráculo recebem
o mesmo hash. Os oráculos quadráticos são interrompidos em `n=512`.

Execução registrada em CPython 3.12.10, Windows 11 `10.0.26300`, com 8 CPUs
lógicas:

| Algoritmo | Implementação | n | Mediana (ms) | Dados SHA-256 |
| --- | --- | ---: | ---: | --- |
| inversões | dividir e conquistar | 128 | 0,8058 | `32f50aa83975dceb` |
| inversões | dividir e conquistar | 512 | 3,0039 | `7924ea51f0dab22c` |
| inversões | dividir e conquistar | 4096 | 35,4772 | `8878253e6c170cb5` |
| inversões | oráculo quadrático | 128 | 1,1253 | `32f50aa83975dceb` |
| inversões | oráculo quadrático | 512 | 21,5998 | `7924ea51f0dab22c` |
| seleção | mediana das medianas | 128 | 0,1338 | `eafbac73d0a148f0` |
| seleção | mediana das medianas | 8192 | 11,4631 | `744a0479423fc240` |
| seleção | oráculo por ordenação | 128 | 0,0061 | `eafbac73d0a148f0` |
| seleção | oráculo por ordenação | 8192 | 0,9774 | `744a0479423fc240` |
| par mais próximo | dividir e conquistar | 64 | 0,4807 | `bdebe6d76ce04ed1` |
| par mais próximo | dividir e conquistar | 512 | 5,1955 | `fe9d719c89c7cafb` |
| par mais próximo | dividir e conquistar | 2048 | 27,9954 | `c4e52378f421a229` |
| par mais próximo | oráculo quadrático | 64 | 1,1991 | `bdebe6d76ce04ed1` |
| par mais próximo | oráculo quadrático | 512 | 49,9511 | `fe9d719c89c7cafb` |

Os dados mostram crescimento bem mais rápido dos dois oráculos quadráticos.
Na seleção, a ordenação da biblioteca padrão foi mais rápida nos tamanhos
medidos apesar do limite assintótico pior: ela é implementada em código nativo
altamente otimizado, enquanto a mediana das medianas cria listas e executa em
Python. Isso exemplifica por que complexidade assintótica e tempo observado
devem ser relatados separadamente.

Para reproduzir toda a série:

```bash
python benchmarks/benchmark_algorithms.py
```

Use `--quick` para validar rapidamente o ambiente. Os hashes devem permanecer
iguais entre execuções com o mesmo código; os tempos não precisam coincidir.

### Limitações

- Foi usado um conjunto pseudoaleatório por tamanho, não todas as distribuições
  ou o pior caso possível.
- As medições incluem validações e alocações internas dos algoritmos, mas não a
  construção inicial dos dados.
- Carga do sistema, frequência do processador, cache, coletor de lixo, versão e
  implementação do Python alteram os tempos.
- A medição não estima memória nem constantes de forma independente.
- Comparar Python puro com `sorted`, implementado em código nativo, não isola
  apenas o efeito da ordem assintótica.
- Séries finitas sugerem tendências, mas não provam limites assintóticos; essa
  garantia vem dos argumentos de corretude e das recorrências anteriores.
