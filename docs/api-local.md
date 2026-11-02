# API local

O servidor do comando `serve` expõe uma API HTTP local para gerar o mesmo
relatório produzido por `audit-report`. A CLI e a API chamam o mesmo serviço de
aplicação; o servidor não reimplementa os algoritmos.

## Limites e segurança

- O corpo completo de cada requisição pode ter no máximo **1 MiB**
  (`1.048.576` bytes).
- `Content-Type` deve ser `application/json` e `Content-Length` é obrigatório.
- O servidor aceita UTF-8 e não suporta `Transfer-Encoding` fragmentado.
- A API não grava uploads, não lê caminhos recebidos e não mantém estado.
- O servidor continua local por padrão em `127.0.0.1` e não oferece TLS ou
  autenticação.

## `POST /api/report`

Cada documento traz um nome de origem, usado nas mensagens e no relatório, e o
conteúdo JSON como string. Para seleção por um critério da matriz:

```json
{
  "inputs": {
    "matrix": {"source": "matriz.json", "content": "{...}"},
    "first_ranking": {"source": "ranking.json", "content": "{...}"},
    "second_ranking": {"source": "ranking-operacional.json", "content": "{...}"},
    "base_weights": {"source": "pesos.json", "content": "{...}"},
    "changed_weights": {"source": "pesos-alterados.json", "content": "{...}"}
  },
  "parameters": {
    "closest_criteria": ["qualidade", "prazo_dias"],
    "selection": {
      "source": {"type": "matrix_criterion", "criterion_id": "qualidade"},
      "percentile": 50
    },
    "include_traces": false
  }
}
```

Para uma coleção externa, inclua `inputs.selection_values`, use
`{"type": "json_list"}` como fonte e informe `k` ou `percentile`. As duas
ordens são mutuamente exclusivas.

Uma requisição válida retorna `200` e o relatório
`ranklab-audit-report` versão 2.

`include_traces` é opcional e vale `false` por padrão. Quando verdadeiro, a
resposta inclui `traces` para comparação de rankings, seleção e par mais
próximo. Acima de 100 itens, o algoritmo ainda é executado, mas seu
rastreamento traz `status: "omitted"`.

## `GET /api/examples/audit-report`

Retorna os documentos conhecidos de `examples/` já montados como uma
requisição de relatório. A lista é fechada no servidor; a rota não aceita
caminhos fornecidos pelo cliente.

## `POST /api/weight-sensitivity`

Recalcula somente a comparação de pesos. O envelope contém `inputs.matrix`,
`inputs.base_weights` e `inputs.changed_weights`, cada qual com `source` e
`content`, seguindo o mesmo formato de `/api/report`. A resposta
`ranklab-weight-sensitivity` versão 1 contém os pesos de entrada e
normalizados, rankings, scores, posições, cruzamentos e Kendall produzidos
por `compare_weight_scenarios`.

## Erros

Erros da API têm formato estável:

```json
{
  "error": {
    "code": "validation_error",
    "message": "matriz.json: items[1].values.custo: valor ausente",
    "input": "matrix",
    "field_path": "items[1].values.custo"
  }
}
```

`input` e `field_path` aparecem quando podem ser determinados. `message`
preserva a mensagem usada pela CLI.

| Status | Significado |
| --- | --- |
| `400` | Envelope ou JSON da requisição inválido |
| `404` | Rota inexistente |
| `411` | `Content-Length` ausente |
| `413` | Requisição acima de 1 MiB |
| `415` | Tipo de conteúdo não suportado |
| `422` | Documento ou parâmetro de análise inválido |
| `500` | Falha inesperada, sem detalhes internos ou stack trace |

O `GET /api/report` existente continua retornando o relatório indicado ao
iniciar o servidor com `--report`.
