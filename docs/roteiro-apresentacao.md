# Roteiro de apresentação — RankLab

Roteiro de aproximadamente 10 minutos, dividido entre Gustavo Xavier
Evangelista e Lucas Andrade Zanetti. Gustavo conduz a interface web; Zanetti
apresenta a implementação dos algoritmos e os testes.

## Preparação antes da gravação

### Gustavo — terminal e navegador

Na raiz do projeto:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ranklab audit-report examples/matriz.json --first-ranking examples/ranking.json --second-ranking examples/ranking-operacional.json --base-weights examples/pesos.json --changed-weights examples/pesos-alterados-muda.json --closest-criteria qualidade prazo_dias --selection-criterion qualidade --percentile 50 --output relatorio.json
python -m ranklab serve --report relatorio.json
```

Abra no navegador o endereço exibido pelo servidor. Deixe o visualizador
carregado com as quatro análises visíveis. O navegador deve ficar em uma
janela separada do editor para que a transição para o código seja clara.

### Zanetti — editor

Deixe abertas as seguintes regiões:

- [`ranking_comparison.py`](../src/ranklab/algorithms/ranking_comparison.py):
  transformação em posições e contagem durante o merge;
- [`deterministic_selection.py`](../src/ranklab/algorithms/deterministic_selection.py):
  mediana das medianas e partição;
- [`closest_pair.py`](../src/ranklab/algorithms/closest_pair.py):
  divisão dos pontos e faixa central;
- [`tests/`](../tests/): testes com oráculos independentes;
- [`reporting.py`](../src/ranklab/reporting.py) e [`server.py`](../src/ranklab/server.py):
  geração do relatório e servidor do visualizador.

## Divisão geral

| Tempo | Tela principal | Quem fala |
| --- | --- | --- |
| 0:00–0:50 | Slide ou README com problema e integrantes | Gustavo |
| 0:50–2:00 | Visualizador web: relatório e cenário | Gustavo |
| 2:00–3:30 | Visualizador web: quatro análises | Gustavo |
| 3:30–4:20 | Visualizador web: formulário e limitações | Gustavo |
| 4:20–6:50 | Código dos três algoritmos | Zanetti |
| 6:50–8:00 | Testes e argumentos de corretude | Zanetti |
| 8:00–9:00 | Complexidade e benchmark | Zanetti |
| 9:00–10:00 | Retorno à interface e conclusão | Gustavo |

## 1. Problema e objetivo — 50 segundos

**Tela:** README, seção “Problema” e identificação dos integrantes.

**Gustavo fala:**

> O RankLab é uma ferramenta acadêmica para analisar rankings e decisões
> multicritério. O objetivo não é escolher automaticamente um fornecedor, mas
> tornar explícitos os dados, os pesos, os algoritmos e as mudanças de
> resultado. Eu sou Gustavo Xavier Evangelista e, junto com Lucas Andrade
> Zanetti, desenvolvi este projeto para a disciplina de Projetos de
> Algoritmos.

> O foco técnico é aplicar algoritmos de dividir e conquistar em três
> problemas: comparação de rankings, seleção de ordem e par mais próximo.

## 2. Cenário e relatório auditável — 1 minuto e 10 segundos

**Tela:** visualizador web aberto no relatório, mostrando o cabeçalho e a
identificação dos dados.

**Gustavo fala:**

> Usaremos um cenário fictício de fornecedores. A matriz contém qualidade e
> prazo de entrega; os rankings e os pesos são arquivos de entrada. Primeiro,
> o comando `audit-report` valida esses documentos e gera um JSON auditável.

> O visualizador não recalcula os algoritmos no navegador. Ele lê o relatório
> produzido pelo servidor, valida sua versão, formata os resultados e mostra
> os parâmetros usados. Isso mantém a implementação central no Python e evita
> duas versões diferentes dos mesmos cálculos.

## 3. Demonstração da interface web — 1 minuto e 30 segundos

**Tela:** seção de comparação de rankings no visualizador.

**Gustavo fala:**

> Nesta seção vemos a divergência entre os rankings. O sistema mostra a
> quantidade de inversões e a distância de Kendall normalizada. Aqui há uma
> inversão entre três pares possíveis, resultando em distância `0,333333`.

**Ação:** rolar até a seção “Par mais próximo”.

**Gustavo fala:**

> O par mais próximo é calculado somente nos dois critérios selecionados,
> depois da normalização das escalas. Portanto, proximidade aqui não significa
> que os fornecedores sejam globalmente semelhantes.

**Ação:** rolar até a seção “Seleção de ordem”.

**Gustavo fala:**

> A seleção encontra o elemento correspondente ao percentil 50. O resultado é
> 90 pontos, na ordem `k=2`. Isso também não transforma a coleção em um
> ranking agregado.

**Ação:** rolar até “Sensibilidade aos pesos”.

**Gustavo fala:**

> Por fim, alteramos os pesos e observamos a mudança de posição. Ao aumentar a
> importância do prazo, o fornecedor B ultrapassa o fornecedor A. O relatório
> mostra os pesos, scores, posições e cruzamentos que explicam essa mudança.

## 4. Formulário e limites do visualizador — 50 segundos

**Tela:** formulário de configuração ou botão “Carregar demonstração”.

**Gustavo fala:**

> Além de abrir um relatório pronto, a interface permite carregar os arquivos
> e configurar os critérios. Também existe uma versão HTML autônoma, que pode
> ser compartilhada sem servidor.

> O visualizador é uma ferramenta local: não possui autenticação, TLS ou
> persistência. Os dados da demonstração são sintéticos e não representam uma
> decisão real de contratação. Se o relatório for inválido ou incompatível, a
> interface exibe um erro explícito em vez de uma seção vazia.

## 5. Transição para o código — 20 segundos

**Tela:** editor de código com `ranking_comparison.py`.

**Gustavo fala:**

> Agora o Zanetti vai mostrar como os resultados são calculados e como os
> testes verificam os contratos dos algoritmos.

## 6. Comparação de rankings — 50 segundos

**Tela:** [`ranking_comparison.py`](../src/ranklab/algorithms/ranking_comparison.py),
função de contagem de inversões.

**Zanetti fala:**

> Primeiro, cada item do primeiro ranking é substituído pela posição que ocupa
> no segundo. Isso produz uma permutação. A contagem de inversões é feita
> durante o merge sort: quando um elemento da metade direita passa à frente
> dos elementos restantes da esquerda, todos esses elementos formam inversões.

> O algoritmo tem tempo `O(n log n)` e espaço auxiliar `O(n)`. Os pares
> explicativos são materializados somente quando a entrada está dentro do
> limite documentado.

## 7. Seleção determinística — 50 segundos

**Tela:** [`deterministic_selection.py`](../src/ranklab/algorithms/deterministic_selection.py),
funções de pivô e partição.

**Zanetti fala:**

> A seleção pela mediana das medianas divide os elementos em grupos de cinco,
> escolhe um pivô determinístico e particiona a entrada em menores, iguais e
> maiores. A recursão continua somente na faixa que contém a ordem procurada.

> Como o pivô garante uma redução suficiente do problema, o pior caso é
> `O(n)`. A partição também trata duplicatas sem recursão infinita e a coleção
> original não é alterada.

## 8. Par mais próximo — 50 segundos

**Tela:** [`closest_pair.py`](../src/ranklab/algorithms/closest_pair.py),
função recursiva e faixa central.

**Zanetti fala:**

> Para o par mais próximo, os pontos são ordenados por X e por Y. O algoritmo
> resolve as duas metades, compara o melhor resultado e examina a faixa central
> para encontrar pares que cruzam a divisão.

> O argumento geométrico limita os sucessores necessários na faixa. O tempo é
> `O(n log n)` e o espaço auxiliar é `O(n)`. A distância depende da
> normalização, dos dois critérios escolhidos e da métrica Euclidiana.

## 9. Testes e corretude — 1 minuto e 10 segundos

**Tela:** testes correspondentes e terminal com o resultado de `pytest`.

**Zanetti fala:**

> A corretude não é inferida apenas pelo tempo observado. Os testes cobrem
> casos normais, limites, entradas inválidas, duplicatas, entradas constantes
> e padrões adversariais.

> Para entradas pequenas, usamos oráculos independentes: enumeração direta de
> pares para inversões e par mais próximo, e ordenação completa para seleção.
> A suíte validada neste clone possui 275 testes aprovados e 16 testes
> ignorados por dependerem de ferramentas opcionais.

> Esses testes aumentam a confiança e detectam regressões, mas os argumentos
> de corretude continuam sendo necessários para justificar o comportamento em
> entradas arbitrárias.

## 10. Complexidade e desempenho — 1 minuto

**Tela:** [`corretude-e-desempenho.md`](corretude-e-desempenho.md) e um dos
gráficos SVG em `artifacts/benchmarks/`.

**Zanetti fala:**

> As complexidades esperadas são `O(n log n)` para inversões e par mais
> próximo, e `O(n)` no pior caso para seleção. Os oráculos quadráticos servem
> como baseline em entradas menores.

> O benchmark registra ambiente, parâmetros, tamanho da entrada e mediana dos
> tempos em JSON. Os gráficos comparam as medições com os baselines e com
> curvas teóricas normalizadas. Essas curvas mostram tendência, não são uma
> previsão de tempo absoluto.

> A medição depende da máquina, da carga do sistema, da versão do Python e
> das constantes de implementação. Portanto, ela não substitui a análise
> assintótica nem prova corretude.

## 11. Encerramento — 1 minuto

**Tela:** voltar ao visualizador web, com o resumo das quatro análises.

**Gustavo fala:**

> O resultado final combina algoritmos, validação, relatório auditável e uma
> interface para leitura. A aplicação mostra de onde vieram os resultados,
> quais parâmetros foram usados e quais limitações devem ser consideradas.

> O RankLab não decide qual fornecedor é correto. Ele ajuda a explicar como
> uma decisão foi produzida e permite comparar cenários de forma reproduzível.

**Zanetti acrescenta:**

> E, do ponto de vista algorítmico, cada resultado é sustentado por uma
> implementação de dividir e conquistar, por argumentos de corretude e por
> testes com oráculos independentes.

## Checklist final

- [ ] Ambiente virtual ativado e dependências instaladas.
- [ ] `python -m pytest -q` executado.
- [ ] Relatório `relatorio.json` gerado.
- [ ] `python -m ranklab serve --report relatorio.json` funcionando.
- [ ] Navegador aberto na página do visualizador.
- [ ] Editor aberto nos arquivos indicados para o Zanetti.
- [ ] Gráficos e documentação disponíveis como plano alternativo.
- [ ] Gravação iniciada somente depois de confirmar que o áudio e a tela estão
      corretos.
