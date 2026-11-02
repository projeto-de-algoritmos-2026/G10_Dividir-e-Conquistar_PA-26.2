# Escopo do projeto

## Objetivo

O RankLab é uma ferramenta acadêmica para tornar auditáveis comparações de
rankings e decisões multicritério. O projeto relaciona uma aplicação de análise
de fornecedores a algoritmos de dividir e conquistar, mantendo separadas as
entradas, os resultados, os argumentos de corretude e as medições empíricas.

## Entregas incluídas

- leitura e validação de matrizes e rankings em JSON e CSV;
- comparação de rankings por contagem de inversões;
- seleção determinística por mediana das medianas;
- par mais próximo em duas dimensões após normalização;
- ranking ponderado e análise de sensibilidade dos pesos;
- relatório JSON auditável com parâmetros, resultados e limitações;
- API local e visualizador web sem dependências de runtime;
- testes automatizados, testes de navegador e integração contínua;
- benchmark reproduzível com dados estruturados e gráficos SVG;
- documentação de contratos, corretude, complexidade, execução e apresentação.

## Fora do escopo

- persistência de dados ou integração com fontes externas;
- autenticação, TLS e implantação como serviço público;
- decisão automática sobre qual fornecedor deve ser escolhido;
- suporte a dados qualitativos ou incompletos sem contrato explícito;
- reimplementação dos algoritmos no JavaScript do visualizador;
- afirmações de desempenho independentes do ambiente de execução.

## Execução de referência

Os comandos de instalação, demonstração, testes, servidor local e benchmark
estão no [`README.md`](../README.md). O backlog histórico e as issues do
repositório estão em [`backlog-issues.md`](backlog-issues.md).
