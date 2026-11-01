# RankLab

Ferramenta acadêmica para auditar rankings e decisões multicritério, desenvolvida na disciplina de Projetos de Algoritmos com foco em **dividir e conquistar**.

## Stack e arquitetura

O projeto usa **Python 3.11 ou superior** e somente a biblioteca padrão em
runtime. A aplicação é uma CLI integrada que valida os dados, executa as
análises e produz um relatório JSON auditável.

O código fica em `src/ranklab/` e é separado por responsabilidade:

- `domain/`: modelos e regras do domínio;
- `algorithms/`: implementações dos algoritmos;
- `io/`: leitura e escrita dos formatos de dados;
- `cli.py`: interface de linha de comando.

Os algoritmos, leitores, modelos e comandos descritos abaixo estão
implementados e cobertos por testes automatizados.

## Requisitos e execução

Pré-requisitos:

- Git;
- Python 3.11 ou superior;
- `pip`, incluído nas instalações usuais do Python.

Para partir de um clone limpo:

```bash
git clone https://github.com/projeto-de-algoritmos-2026/G10_Dividir-e-Conquistar_PA-26.2.git
cd G10_Dividir-e-Conquistar_PA-26.2
python -m venv .venv
```

Ative o ambiente virtual no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Ou em Linux/macOS:

```bash
source .venv/bin/activate
```

Instale o projeto e as ferramentas de desenvolvimento:

```bash
python -m pip install -e ".[dev]"
```

Confirme a instalação:

```bash
python -m ranklab --info
python -m ranklab --help
```

O executável `ranklab` também é instalado, mas os exemplos usam
`python -m ranklab` para não depender da configuração de `PATH`.

## Demonstração ponta a ponta

Os arquivos em [`examples/`](examples/README.md) formam um cenário fictício de
avaliação de fornecedores. A origem, licença e relação entre os arquivos estão
documentadas no próprio diretório.

Carregue e valide as entradas:

```bash
python -m ranklab load-matrix examples/matriz.json
python -m ranklab load-ranking examples/ranking.json
python -m ranklab load-ranking examples/ranking-operacional.json
```

Execute cada análise:

```bash
python -m ranklab compare-rankings examples/ranking.json examples/ranking-operacional.json
python -m ranklab closest-pair examples/matriz.json qualidade prazo_dias
python -m ranklab select examples/valores-qualidade.json --percentile 50
python -m ranklab compare-weights examples/matriz.json --base-weights examples/pesos.json --changed-weights examples/pesos-alterados-muda.json
```

O relatório auditável reúne as quatro análises em uma execução:

```bash
python -m ranklab audit-report examples/matriz.json --first-ranking examples/ranking.json --second-ranking examples/ranking-operacional.json --base-weights examples/pesos.json --changed-weights examples/pesos-alterados-muda.json --closest-criteria qualidade prazo_dias --selection-criterion qualidade --percentile 50
```

Resultados de referência:

- os rankings têm uma inversão entre três pares possíveis e distância de
  Kendall `0,333333`;
- `fornecedor-a` e `fornecedor-c` são o par mais próximo nos dois critérios;
- o percentil 50 da qualidade é `90` pontos, na ordem `k=2`;
- ao dar maior peso ao prazo, `fornecedor-b` ultrapassa `fornecedor-a`.

Esses resultados respondem perguntas diferentes. Proximidade não é qualidade
geral, seleção não é ranking agregado e sensibilidade não define o peso
correto; o relatório preserva essa separação.

## Testes e avaliação

Execute toda a suíte automatizada a partir da raiz:

```bash
python -m pytest -q
```

Para validar somente inversões, seleção e par mais próximo:

```bash
python -m pytest -q tests/test_ranking_comparison.py tests/test_deterministic_selection.py tests/test_closest_pair.py
```

O benchmark determinístico fica separado dos testes para não impor limites de
tempo dependentes da máquina:

```bash
python benchmarks/benchmark_algorithms.py
```

Os contratos, invariantes, provas, complexidades, resultados empíricos e
limitações estão no
[`docs/corretude-e-desempenho.md`](docs/corretude-e-desempenho.md).

## Convenções de contribuição

- Use branches curtas com prefixo `feat/`, `fix/` ou `docs/` e um resumo em kebab-case.
- Faça commits pequenos, com mensagens no imperativo e escopo claro (por exemplo, `docs: especifica contrato de rankings`).
- Abra um pull request por conjunto coeso de mudanças; peça revisão de outro integrante antes de integrar.
- Registre decisões de domínio e formato na documentação antes de usá-las em algoritmos.

## Contratos de entrada

Os contratos de ranking e matriz de pontuação, as políticas para empates e
dados ausentes e exemplos válidos estão em
[`docs/contratos-dados.md`](docs/contratos-dados.md).

A comparação de rankings, sua API, prova de corretude, complexidade e exemplos
estão documentados em
[`docs/comparacao-rankings.md`](docs/comparacao-rankings.md).

A seleção determinística e a proximidade numérica em duas dimensões estão
documentadas em [`docs/selecao-mediana.md`](docs/selecao-mediana.md) e
[`docs/par-mais-proximo.md`](docs/par-mais-proximo.md).

A regra de normalização, pesos, score e desempate do ranking agregado está
documentada em
[`docs/ranking-agregado.md`](docs/ranking-agregado.md).

A comparação entre configurações de pesos, incluindo mudanças por item,
cruzamentos e divergência por inversões, está documentada em
[`docs/sensibilidade-pesos.md`](docs/sensibilidade-pesos.md).

O relatório JSON que reúne as quatro análises, seus parâmetros e limitações
está documentado em
[`docs/relatorio-auditavel.md`](docs/relatorio-auditavel.md).

O roteiro sugerido para a demonstração está em
[`docs/roteiro-apresentacao.md`](docs/roteiro-apresentacao.md).

## Problema

Organizações ordenam fornecedores, candidatos, produtos e projetos usando critérios que podem ter pesos e escalas diferentes. O RankLab pretende tornar essas decisões mais transparentes: comparar rankings, mostrar mudanças de posição e analisar a sensibilidade do resultado a alterações nos pesos.

## Algoritmos centrais implementados

| Necessidade | Técnica | Resultado esperado |
| --- | --- | --- |
| Comparar dois rankings | Merge sort com contagem de inversões | Número de pares com ordem discordante e distância de Kendall normalizada |
| Selecionar posição/percentil | Mediana das medianas (seleção determinística) | Elemento de ordem `k`, sem ordenar toda a entrada |
| Achar perfis numéricos próximos | Par mais próximo, após normalização | Par de itens com menor distância segundo a métrica escolhida |
| Agregar pontuações multicritério | Min-max orientada e soma ponderada | Ranking auditável com valores normalizados, pesos e score |

## Limites conhecidos

- A comparação por inversões só é definida para rankings dos mesmos itens; itens ausentes, duplicados e empates exigem tratamento explícito.
- Similaridade entre pontuações não implica similaridade real entre os objetos. A análise de par próximo depende da escolha de atributos, da normalização e da métrica.
- A seleção de ordem resume uma coleção conforme `k` ou percentil; ela não deve ser apresentada como um ranking agregado sem uma regra explícita.
- Alterações de pesos precisam respeitar uma regra documentada de agregação multicritério.
- A soma ponderada é compensatória: desempenho alto em um critério pode compensar desempenho baixo em outro, conforme os pesos definidos.
- O MVP aceita apenas JSON pela linha de comando; não há interface gráfica,
  persistência ou integração com fontes externas.
- Os dados da demonstração são sintéticos e não validam decisões reais de
  contratação.
- Medições de desempenho dependem da máquina e não substituem a análise
  assintótica.

## Contexto acadêmico

Projeto em grupo para a disciplina de Projetos de Algoritmos. O objetivo é relacionar uma aplicação de análise de decisões a algoritmos de dividir e conquistar, com especificação e avaliação de corretude e complexidade.
