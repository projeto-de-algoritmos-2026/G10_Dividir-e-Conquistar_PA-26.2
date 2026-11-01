# Dados de demonstração

Os arquivos deste diretório descrevem um cenário inteiramente fictício de
avaliação de três fornecedores. Todos os nomes, identificadores, rankings e
valores foram criados pelo Grupo RankLab para demonstrar os algoritmos; eles
não representam empresas, contratos ou medições reais.

## Origem e licença

- **Origem:** dados sintéticos produzidos pelo Grupo RankLab em 2026.
- **Licença:** os arquivos são distribuídos sob a licença MIT do repositório,
  disponível em [`../LICENSE`](../LICENSE).
- **Finalidade:** demonstração acadêmica. Os resultados não devem fundamentar
  decisões reais de contratação.

## Arquivos

| Arquivo | Papel na demonstração |
| --- | --- |
| `matriz.json` | Qualidade técnica e prazo de entrega dos fornecedores. |
| `ranking.json` | Ranking da avaliação técnica. |
| `ranking-operacional.json` | Ranking da avaliação operacional. |
| `valores-qualidade.json` | Lista derivada da coluna `qualidade`, usada pelo comando `select`. |
| `pesos.json` | Cenário-base, com maior peso para qualidade. |
| `pesos-alterados-muda.json` | Cenário alternativo, com maior peso para prazo. |
| `pesos-alterados-estavel.json` | Cenário alternativo que muda scores sem mudar a ordem. |

## Resultados de referência

- Os rankings técnico e operacional divergem no par
  `fornecedor-a`/`fornecedor-b`: uma inversão entre três pares possíveis.
- Em `qualidade` e `prazo_dias`, o par mais próximo é
  `fornecedor-a`/`fornecedor-c`.
- A segunda qualidade, ou percentil 50 pelo posto mais próximo, é `90` pontos.
- Ao trocar os pesos de `2:1` para `1:3`, `fornecedor-b` ultrapassa
  `fornecedor-a` no ranking agregado.
