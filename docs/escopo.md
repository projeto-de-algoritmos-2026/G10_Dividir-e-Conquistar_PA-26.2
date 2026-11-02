# Escopo e definições do RankLab

## Objetivo

Investigar como rankings e decisões multicritério mudam quando se alteram critérios, pesos ou dados. O sistema deve mostrar resultados reproduzíveis e explicar qual medida está sendo apresentada.

## Entradas e modelo conceitual

- **Item:** entidade identificada de forma única (por exemplo, fornecedor ou proposta).
- **Ranking:** sequência ordenada de identificadores, opcionalmente acompanhada de posições ou pontuações.
- **Matriz de pontuação:** uma linha por item e uma coluna por critério, com valores numéricos e metadados dos critérios.
- **Critério:** atributo com direção de preferência (maior é melhor ou menor é melhor), escala/unidade e peso quando houver agregação.

Formatos concretos de arquivo, tratamento de valores ausentes e validações serão definidos antes da implementação da importação.

## Definições algorítmicas

### Contagem de inversões entre rankings

Para rankings completos dos mesmos `n` itens, converta o segundo ranking em um mapa `item -> posição`. Reescreva o primeiro como a sequência dessas posições. Cada inversão na sequência corresponde a um par de itens cuja ordem relativa é diferente nos dois rankings. Conte-as por merge sort em `O(n log n)` tempo e `O(n)` espaço auxiliar.

A distância de Kendall normalizada pode ser reportada como `inversões / (n(n-1)/2)` para `n >= 2`. Para `n < 2`, a convenção de saída precisa ser documentada. Rankings com empates ou cobertura diferente requerem uma política explícita antes da comparação; não se deve aplicar silenciosamente a fórmula de ranking estrito.

### Seleção pela mediana das medianas

Defina o contrato como seleção do elemento de ordem `k` (ou percentil convertido para `k`) em uma coleção não ordenada. A seleção determinística por grupos de cinco garante tempo `O(n)` no pior caso. Diferencie o valor/elemento selecionado da posição mediana de um item em várias listas: são análises distintas e podem exigir agregação separada.

### Par mais próximo de perfis

Compare vetores numéricos de atributos escolhidos, não os objetos em sentido amplo. Documente a normalização (por exemplo, min-max ou z-score), a distância (por exemplo, Euclidiana) e o tratamento de atributos ausentes/constantes. A implementação por dividir e conquistar pode usar a formulação geométrica clássica em duas dimensões (`O(n log n)`); para dimensão maior, a complexidade e a estratégia mudam, então o escopo dimensional precisa ser fixado.

## Análise de sensibilidade

Uma regra de agregação inicial precisa ser escolhida e documentada antes da implementação. Para pontuações normalizadas `s(i,j)` e pesos não negativos `w(j)` com soma 1, uma opção simples é `score(i) = Σ w(j) * s(i,j)`. A interface deve permitir comparar uma configuração base com uma configuração alterada e apontar mudanças de posição, empates e itens afetados. A normalização por critério e a direção de preferência fazem parte do modelo, não são detalhes invisíveis.

## Relatório e interpretação

O resultado deve manter separadas pelo menos estas perguntas:

1. **Divergência de ordenação:** quantos pares inverteram de ordem entre dois rankings?
2. **Proximidade de pontuação/perfil:** quais vetores de atributos são próximos sob a normalização e métrica declaradas?
3. **Posição mediana:** qual elemento ocupa a ordem `k` na coleção analisada, ou qual posição agregada foi calculada?
4. **Sensibilidade:** que itens e posições mudaram após uma configuração de pesos ser alterada?

Nenhuma dessas medidas, isoladamente, determina qual decisão é “correta”. O relatório deve informar entradas e parâmetros usados para que a análise possa ser reproduzida.

## Avaliação acadêmica

Para cada algoritmo, registrar: problema e contrato de entrada/saída, ideia de dividir e conquistar, prova ou argumento de corretude, recorrência/complexidade de tempo e espaço, casos de borda e exemplos que permitam verificar o resultado. A comparação empírica deve separar custo do algoritmo de custo de importação, normalização e apresentação.
