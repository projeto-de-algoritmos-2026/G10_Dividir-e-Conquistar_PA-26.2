# Par de perfis mais próximo em duas dimensões

## Contrato e política

`closest_pair(matrix, (criterion_x, criterion_y))` recebe exatamente dois
critérios quantitativos da `ScoringMatrix`, normaliza cada coluna por
min-max e calcula distância Euclidiana. A direção do critério é respeitada:
`lower_is_better` inverte o eixo, sem mudar a noção de proximidade. Uma
coluna constante é projetada em zero, pois não distingue os perfis. A matriz
já rejeita valores ausentes e não numéricos na leitura.

O resultado informa os dois `item_id`, a distância, os critérios, a
normalização e a métrica. Menos de dois itens, critérios inexistentes,
duplicados ou em quantidade diferente de dois são erros. Em empate de
distância, vence o par lexicograficamente menor. O resultado descreve
proximidade numérica nos dois atributos escolhidos; não é uma medida de
similaridade geral dos objetos.

## Corretude e complexidade

Os pontos são inicialmente ordenados por `x` e por `y`. A recursão divide no
meio, encontra o melhor par em cada metade e examina a faixa central. Na
faixa, a ordenação por `y` limita a quantidade de vizinhos que precisa ser
comparada; portanto nenhum par potencialmente melhor é ignorado. O menor
par das três possibilidades (esquerda, direita e faixa) é o resultado.

As ordenações iniciais custam `O(n log n)` e cada nível da recursão filtra e
varre a faixa em `O(n)`, resultando em `O(n log n)` de tempo e `O(n)` de
espaço.
