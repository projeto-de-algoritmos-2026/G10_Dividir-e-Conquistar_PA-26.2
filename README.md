# RankLab

Ferramenta acadêmica para auditar rankings e decisões multicritério, desenvolvida na disciplina de Projetos de Algoritmos com foco em **dividir e conquistar**.

## Stack e arquitetura

O projeto usa **Python 3.11 ou superior**. A linguagem permite expressar os algoritmos da disciplina com clareza, enquanto a biblioteca padrão mantém a instalação simples e reproduzível. A primeira entrega é uma interface de linha de comando, adequada para demonstrar entradas, saídas e resultados sem adicionar uma interface gráfica antes de os contratos do domínio estarem definidos.

O código fica em `src/ranklab/` e é separado por responsabilidade:

- `domain/`: modelos e regras do domínio;
- `algorithms/`: implementações dos algoritmos;
- `io/`: leitura e escrita dos formatos de dados;
- `cli.py`: interface de linha de comando.

Os diretórios de domínio, algoritmos e entrada/saída serão preenchidos conforme as respectivas issues forem implementadas. A CLI atual é um esqueleto executável.

## Requisitos e execução

É necessário ter Python 3.11 ou superior. Para instalar em modo editável a partir da raiz do repositório:

```bash
python -m pip install -e .
```

Em seguida, execute:

```bash
ranklab --help
ranklab --info
```

Também é possível iniciar sem instalar o comando:

```bash
PYTHONPATH=src python -m ranklab --info
```

O projeto não requer dependências de runtime além da biblioteca padrão do Python.

## Convenções de contribuição

- Use branches curtas com prefixo `feat/`, `fix/` ou `docs/` e um resumo em kebab-case.
- Faça commits pequenos, com mensagens no imperativo e escopo claro (por exemplo, `docs: especifica contrato de rankings`).
- Abra um pull request por conjunto coeso de mudanças; peça revisão de outro integrante antes de integrar.
- Registre decisões de domínio e formato na documentação antes de usá-las em algoritmos.

## Contratos de entrada

Os contratos de ranking e matriz de pontuação, as políticas para empates e dados ausentes e exemplos válidos estão em [`docs/contratos-dados.md`](docs/contratos-dados.md). O escopo conceitual está em [`docs/escopo.md`](docs/escopo.md).

## Problema

Organizações ordenam fornecedores, candidatos, produtos e projetos usando critérios que podem ter pesos e escalas diferentes. O RankLab pretende tornar essas decisões mais transparentes: comparar rankings, mostrar mudanças de posição e analisar a sensibilidade do resultado a alterações nos pesos.

## Algoritmos centrais previstos

| Necessidade | Técnica | Resultado esperado |
| --- | --- | --- |
| Comparar dois rankings | Merge sort com contagem de inversões | Número de pares com ordem discordante; distância de Kendall normalizada opcional |
| Selecionar posição/percentil | Mediana das medianas (seleção determinística) | Elemento de ordem `k`, sem ordenar toda a entrada |
| Achar perfis numéricos próximos | Par mais próximo, após normalização | Par de itens com menor distância segundo a métrica escolhida |

## Limites conhecidos

- A comparação por inversões só é definida para rankings dos mesmos itens; itens ausentes, duplicados e empates exigem tratamento explícito.
- Similaridade entre pontuações não implica similaridade real entre os objetos. A análise de par próximo depende da escolha de atributos, da normalização e da métrica.
- A posição mediana resume posições ou valores conforme a definição escolhida; ela não deve ser apresentada como um ranking agregado sem uma regra explícita.
- Alterações de pesos precisam respeitar uma regra documentada de agregação multicritério.

## Contexto acadêmico

Projeto em grupo para a disciplina de Projetos de Algoritmos. O objetivo é relacionar uma aplicação de análise de decisões a algoritmos de dividir e conquistar, com especificação e avaliação de corretude e complexidade.
