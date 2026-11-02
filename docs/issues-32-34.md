# Extensões das issues 32–34

## Vários rankings

`ranklab aggregate-rankings R1.json R2.json ...` calcula a matriz simétrica de
distâncias de Kendall e agrega cada item pela posição mediana. Para um número
par de rankings é usada a mediana inferior (`ceil(n/2)`); empates são
desempatados por `item_id`. Isto é uma agregação de posições, não um ranking
ponderado.

## Pontos de virada

`ranklab turning-points matriz.json --base-weights base.json
--changed-weights alterados.json` interpola os pesos em `t ∈ [0,1]`. Cada
cruzamento de scores é calculado exatamente; os intervalos exibidos usam
desempate lexicográfico em um ponto interno.

## Empates

`ranklab compare-rankings-tau-b` calcula Kendall tau-b, separando pares
concordantes, discordantes e empatados. Tau-b é `0` quando o denominador é
zero. O formato JSON v1 continua estrito; rankings com empates podem ser
construídos pela API para a análise explícita.
