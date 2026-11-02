# Conjunto ampliado de demonstração

Cenário fictício com **32 fornecedores**, gerado para expor vários níveis de
recursão nos algoritmos de dividir e conquistar. Os valores não representam
empresas, contratos ou medições reais e **não sustentam decisões reais**.

## Origem, licença e transformações

| Campo | Conteúdo |
| --- | --- |
| Origem | Dados sintéticos produzidos pelo Grupo RankLab. |
| Semente | `20261102`, fixa no gerador `generate_demo.py`. |
| Licença | MIT do repositório ([`../../LICENSE`](../../LICENSE)). |
| Transformações | Amostragem uniforme de qualidade ∈ [55, 98] e prazo ∈ [5, 40]; o par `fornecedor-01`/`fornecedor-02` é ajustado manualmente para ficar quase colado após a normalização; rankings técnico e operacional são derivações determinísticas da matriz (qualidade desc. e prazo asc.); pesos são escolhas didáticas. |
| Limitações | Não há coleta empírica, amostragem representativa nem validação externa. Use apenas em aula e em testes. |

Para regenerar os arquivos a partir da semente:

```bash
python examples/large/generate_demo.py
```

## Por que 32 itens?

O caso-base do par mais próximo compara diretamente coleções com `n ≤ 3`, então
`n = 32` produz vários níveis de divisão (profundidade máxima observada: 4). A
mediana das medianas trabalha em grupos de cinco e também recorre (profundidade
observada: 2). Com três itens, esses níveis quase não aparecem.

Os números de referência conferidos pelos oráculos e pelos algoritmos estão em
[`reference.json`](reference.json). `tests/test_large_demo.py` confere esses
números e regenera os arquivos a partir da semente para compará-los com os
versionados.

## Arquivos

| Arquivo | Papel |
| --- | --- |
| `matriz.json` | Qualidade e prazo dos 32 fornecedores. |
| `ranking.json` | Ranking técnico (qualidade decrescente). |
| `ranking-operacional.json` | Ranking operacional (prazo crescente). |
| `valores-qualidade.json` | Coluna `qualidade`, para `select`. |
| `pesos.json` | Cenário-base (qualidade 3 : prazo 1). |
| `pesos-alterados-muda.json` | Maior peso ao prazo; altera a ordem agregada. |
| `pesos-alterados-estavel.json` | Pequeno reforço da qualidade; não altera a ordem. |
| `generate_demo.py` | Gerador reproduzível. |
| `reference.json` | Metadados e resultados de referência. |

## Comandos de conferência

```bash
python -m ranklab load-matrix examples/large/matriz.json
python -m ranklab compare-rankings examples/large/ranking.json examples/large/ranking-operacional.json
python -m ranklab closest-pair examples/large/matriz.json qualidade prazo_dias
python -m ranklab select examples/large/valores-qualidade.json --percentile 50
python -m ranklab compare-weights examples/large/matriz.json --base-weights examples/large/pesos.json --changed-weights examples/large/pesos-alterados-muda.json
python -m ranklab compare-weights examples/large/matriz.json --base-weights examples/large/pesos.json --changed-weights examples/large/pesos-alterados-estavel.json
python -m ranklab audit-report examples/large/matriz.json --first-ranking examples/large/ranking.json --second-ranking examples/large/ranking-operacional.json --base-weights examples/large/pesos.json --changed-weights examples/large/pesos-alterados-muda.json --closest-criteria qualidade prazo_dias --selection-criterion qualidade --percentile 50 --output relatorio-large.json
```

O campo `origin` da matriz e dos rankings, repetido no relatório auditável,
declara que os dados são sintéticos e não sustentam decisões reais.
