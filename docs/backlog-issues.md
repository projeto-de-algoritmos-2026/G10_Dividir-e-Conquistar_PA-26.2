# Backlog inicial de issues — RankLab

> Espelho local das 12 issues publicadas no GitHub. Os títulos usam fases para manter o backlog agrupado; a ordem sugerida pode ser ajustada conforme as decisões do grupo.

## Issues publicadas

1. [#1 — Definir stack, arquitetura mínima e como executar](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/1)
2. [#2 — Especificar modelo comum e formatos de entrada](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/2)
3. [#3 — Implementar importação e validação](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/3)
4. [#4 — Comparar rankings por merge sort e inversões](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/4)
5. [#5 — Seleção pela mediana das medianas](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/5)
6. [#6 — Par de perfis mais próximo em duas dimensões](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/6)
7. [#7 — Normalização e ranking ponderado](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/7)
8. [#8 — Análise de sensibilidade dos pesos](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/8)
9. [#9 — Visualizar comparação e mudanças de posição](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/9)
10. [#10 — Relatório auditável](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/10)
11. [#11 — Corretude, casos de referência e complexidade](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/11)
12. [#12 — Integração ponta a ponta e demonstração](https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2/issues/12)

## Fase 0 — Fundação

### [Fase 0 — Fundação] Definir stack, arquitetura mínima e como executar o projeto

**Objetivo:** Escolher e registrar a tecnologia do RankLab e preparar o repositório para que os dois integrantes consigam desenvolver e executar a mesma versão.

**Atividades:**
- Comparar opções de linguagem e interface considerando a disciplina, familiaridade do grupo e facilidade de demonstrar os algoritmos.
- Escolher a stack e registrar os motivos.
- Separar domínio, algoritmos, entrada/saída e apresentação de acordo com a stack escolhida.
- Criar esqueleto executável e documentar instalação e execução.
- Definir convenções simples de branches, nomes e revisão entre integrantes.

**Critérios de aceite:**
- [ ] Stack, justificativa e estrutura estão documentadas.
- [ ] Um clone limpo consegue instalar dependências e iniciar a aplicação conforme o README.
- [ ] A estrutura atende ao escopo sem abstrações desnecessárias.

**Dependências:** Nenhuma; inicia a implementação.

## Fase 1 — Dados

### [Fase 1 — Dados] Especificar modelo comum e formatos de entrada

**Objetivo:** Definir contratos para importar rankings e matrizes de pontuação sem ambiguidades.

**Atividades:**
- Especificar identificadores únicos, nomes dos rankings, posições e origem.
- Especificar matriz: itens, critérios, valores e metadados (unidade/escala e direção maior-melhor ou menor-melhor).
- Escolher formatos mínimos de importação e documentar exemplos válidos.
- Definir tratamento de empate, item ausente, célula vazia, valor inválido e precisão.
- Definir campos obrigatórios e mensagens de erro.

**Critérios de aceite:**
- [ ] Contratos documentados para ranking e matriz.
- [ ] Um exemplo fictício válido para cada formato.
- [ ] Política de empate e dados ausentes explícita.
- [ ] Identificadores compatíveis entre comparação, agregação e proximidade.

**Dependências:** Fase 0 — stack escolhida.

### [Fase 1 — Dados] Implementar importação e validação dos arquivos

**Objetivo:** Carregar os formatos definidos e rejeitar entradas que produziriam resultados enganosos.

**Atividades:**
- Implementar leitores para os formatos acordados.
- Validar cabeçalhos, tipos, identificadores duplicados, linhas inconsistentes e valores numéricos.
- Conferir conjunto de itens em rankings comparados, conforme política definida.
- Apresentar erros úteis, apontando linha/coluna quando possível.
- Separar leitura da lógica dos algoritmos.

**Critérios de aceite:**
- [ ] Arquivos válidos viram o modelo comum.
- [ ] Entradas inválidas não geram resultados silenciosamente incorretos.
- [ ] Erros ajudam a localizar o problema.
- [ ] Exemplos documentados podem ser carregados pela aplicação.

**Dependências:** Modelo e formatos definidos; Fase 0.

## Fase 2 — Algoritmos de dividir e conquistar

### [Fase 2 — Algoritmos] Comparar rankings por merge sort e contagem de inversões

**Objetivo:** Comparar dois rankings estritos dos mesmos itens pela contagem eficiente de pares discordantes.

**Contrato:** Mapear item para posição no segundo ranking e converter o primeiro em uma sequência dessas posições. Uma inversão equivale a um par cuja ordem relativa diverge. Aplicar a política de cobertura e empate do MVP.

**Atividades:**
- Implementar contagem integrada ao merge sort: O(n log n) tempo e O(n) espaço auxiliar.
- Retornar a quantidade e, para conjuntos de tamanho razoável, os pares invertidos que explicam a divergência.
- Calcular distância normalizada de Kendall como inversões / (n(n-1)/2), com convenção documentada para n menor que 2.
- Tratar rankings iguais, ordem reversa e entrada incompatível.
- Registrar argumento de corretude e análise de complexidade.

**Critérios de aceite:**
- [ ] Contagem equivale ao número de pares discordantes.
- [ ] Exemplos pequenos mostram cada par contado.
- [ ] Casos de borda e normalização estão documentados.
- [ ] Conjuntos diferentes e rankings inválidos são rejeitados.

**Dependências:** Modelo de dados e política de empate/cobertura.

### [Fase 2 — Algoritmos] Implementar seleção determinística pela mediana das medianas

**Objetivo:** Selecionar o elemento de ordem k sem ordenar toda a coleção, usando seleção determinística por grupos de cinco.

**Atividades:**
- Definir indexação de k e conversão de percentis em k.
- Implementar escolha do pivô por grupos, particionamento e seleção recursiva.
- Definir comportamento para duplicatas, coleção vazia e k inválido.
- Exibir valor/elemento selecionado e sua ordem, sem confundir com ranking agregado.
- Documentar corretude e recorrência que garante O(n) no pior caso.

**Critérios de aceite:**
- [ ] Contratos de k, percentil e duplicatas documentados.
- [ ] Resultado correto em exemplos e casos de borda.
- [ ] A coleção não é ordenada inteira como atalho.
- [ ] Relatório explica pivô e garantia de tempo linear.

**Dependências:** Fase 0; implementação pode ocorrer independentemente da interface.

### [Fase 2 — Algoritmos] Encontrar par de perfis mais próximo em duas dimensões

**Objetivo:** Aplicar o algoritmo clássico de par mais próximo por dividir e conquistar com escopo e métrica explícitos.

**Escopo do MVP:** Usar exatamente dois atributos quantitativos, normalizados antes do algoritmo, com distância Euclidiana. O resultado significa perfis próximos nesses atributos, não similaridade geral dos objetos.

**Atividades:**
- Definir atributos e normalização; explicar valores ausentes e colunas constantes.
- Implementar divisão, recursão e análise da faixa central, com ordenação inicial apropriada.
- Retornar os dois identificadores e a distância.
- Tratar menos de dois itens, pontos duplicados e empate de distância.
- Documentar corretude e complexidade O(n log n) em duas dimensões.

**Critérios de aceite:**
- [ ] Resultado identifica atributos, normalização e métrica.
- [ ] Implementação segue dividir e conquistar e mantém complexidade esperada.
- [ ] Casos de borda e escalas constantes têm política definida.
- [ ] Interface não chama proximidade numérica de similaridade geral.

**Dependências:** Modelo de matriz e regra de normalização definida.

## Fase 3 — Decisão multicritério

### [Fase 3 — Decisão multicritério] Definir normalização e calcular ranking ponderado

**Objetivo:** Definir uma regra transparente e reproduzível para transformar pontuações em ranking agregado.

**Atividades:**
- Selecionar normalização por critério (por exemplo, min-max) e tratar colunas constantes e dados ausentes.
- Respeitar direção de preferência de cada critério.
- Definir pesos não negativos e validação/normalização para soma 1.
- Calcular score agregado por soma ponderada e ordenar itens, especificando empate.
- Mostrar valores normalizados, pesos e score.

**Critérios de aceite:**
- [ ] Fórmula, direção, normalização e política de empate documentadas.
- [ ] Pesos inválidos são rejeitados ou corrigidos segundo regra documentada.
- [ ] Exemplos pequenos podem ser conferidos manualmente.
- [ ] Mesmos dados e parâmetros produzem o mesmo ranking.

**Dependências:** Modelo de matriz e metadados de critério.

### [Fase 3 — Decisão multicritério] Implementar análise de sensibilidade dos pesos

**Objetivo:** Comparar ranking agregado em configuração base com ranking após alteração dos pesos.

**Atividades:**
- Criar fluxo para definir pesos base e variação, mantendo as regras de soma e validação.
- Recalcular scores e rankings para ambas as configurações.
- Identificar itens que mudaram de posição, variação de score e cruzamento de posições relevantes.
- Exibir divergência entre rankings usando a contagem de inversões.
- Identificar parâmetros usados em cada cenário.

**Critérios de aceite:**
- [ ] Configuração base e alterada são comparáveis lado a lado.
- [ ] Mudanças de posição e divergência são explicadas por item.
- [ ] Normalização, direções e política de empate são preservadas.
- [ ] Há exemplo em que alterar peso muda a ordem e outro em que não muda.

**Dependências:** Ranking ponderado e algoritmo de comparação.

## Fase 4 — Experiência e relatório

### [Fase 4 — Experiência] Criar visualização de comparação e mudanças de posição

**Objetivo:** Apresentar comparação compreensível dos rankings e mostrar quais itens trocaram de posição.

**Atividades:**
- Permitir selecionar dois rankings/configurações.
- Exibir posições lado a lado e variação por identificador de item.
- Mostrar total de inversões e Kendall normalizado com rótulos e explicação.
- Destacar pares discordantes ou listar mudanças, considerando volume de dados.
- Exibir estados de erro, carregamento e ausência de dados.

**Critérios de aceite:**
- [ ] Origem dos rankings é clara.
- [ ] Posições alteradas podem ser localizadas sem inferir pelo total agregado.
- [ ] Medidas brutas e normalizadas têm nomes distintos.
- [ ] Erros não são apresentados como se fossem resultados vazios.

**Dependências:** Importação, algoritmo de comparação e agregação; integrar sensibilidade quando pronta.

### [Fase 4 — Experiência] Montar relatório auditável das análises

**Objetivo:** Reunir resultados sem misturar divergência de ordem, proximidade, posição mediana e sensibilidade.

**Atividades:**
- Criar relatório/visão que identifique a pergunta respondida por cada medida.
- Informar entradas, critérios, pesos, normalização, métrica e políticas aplicadas.
- Diferenciar resultados de interpretação e apresentar limitações do par próximo.
- Permitir consultar detalhes dos itens afetados e valores de origem.
- Definir exportação somente se couber no MVP; caso contrário, documentar decisão.

**Critérios de aceite:**
- [ ] As quatro análises têm seções e definições distintas.
- [ ] Resultados são reproduzíveis a partir dos parâmetros informados.
- [ ] Proximidade em atributos não é apresentada como similaridade geral.
- [ ] Limitações e casos não suportados estão acessíveis.

**Dependências:** Algoritmos e análise multicritério integrados.

## Fase 5 — Avaliação e entrega

### [Fase 5 — Avaliação] Registrar corretude, casos de referência e complexidade

**Objetivo:** Produzir evidências de que as implementações atendem aos contratos e analisar custo assintótico.

**Atividades:**
- Especificar invariantes/argumentos de corretude para inversões, seleção e par mais próximo.
- Criar testes automatizados determinísticos, com casos manuais, oráculos simples e entradas adversariais.
- Comparar inversões com contagem quadrática em entradas pequenas.
- Comparar seleção com o elemento da posição correspondente após ordenação em entradas pequenas.
- Comparar par mais próximo com busca quadrática em dados pequenos.
- Registrar complexidade de tempo/espaço e limites da avaliação empírica.

**Critérios de aceite:**
- [ ] Cada algoritmo cobre casos normais, limites e entradas inválidas.
- [ ] Oráculos independentes conferem resultados em entradas pequenas.
- [ ] Testes rodam pelo comando documentado.
- [ ] Relatório separa prova de corretude da medição de desempenho.

**Dependências:** Três algoritmos implementados e stack definida.

### [Fase 5 — Entrega] Integrar fluxo ponta a ponta e preparar demonstração acadêmica

**Objetivo:** Integrar a aplicação e preparar uma demonstração que evidencie a utilidade e os algoritmos do projeto.

**Atividades:**
- Selecionar conjunto fictício ou público com origem/licença documentada.
- Demonstrar carregamento, comparação, par próximo, seleção de posição e variação de pesos.
- Resolver inconsistências entre modelo e interface e registrar limitações do MVP.
- Atualizar README com pré-requisitos, instalação, execução e exemplos.
- Preparar roteiro de apresentação com aplicação, dividir e conquistar, corretude e complexidade.

**Critérios de aceite:**
- [ ] Clone limpo executa a demonstração seguindo o README.
- [ ] Fluxo ponta a ponta funciona com os dados de demonstração.
- [ ] Resultados e parâmetros são interpretáveis.
- [ ] Apresentação separa implementação, corretude e desempenho.

**Dependências:** MVP integrado das Fases 1 a 4 e avaliação da Fase 5.
