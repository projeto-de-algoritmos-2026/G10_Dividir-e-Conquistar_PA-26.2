# Visualizador web

O comando `serve` abre no navegador o relatório gerado por `audit-report`. Cada
análise aparece em uma seção própria, com sua pergunta, resposta, evidências e
parâmetros, seguindo a separação descrita em
[`relatorio-auditavel.md`](relatorio-auditavel.md).

## Uso

```bash
python -m ranklab audit-report examples/matriz.json --first-ranking examples/ranking.json --second-ranking examples/ranking-operacional.json --base-weights examples/pesos.json --changed-weights examples/pesos-alterados-muda.json --closest-criteria qualidade prazo_dias --selection-criterion qualidade --percentile 50 --output relatorio.json
python -m ranklab serve --report relatorio.json
```

Acesse o endereço impresso pelo comando. Sem `--report`, a página pede que um
relatório seja escolhido em "Abrir relatório".

| Opção | Padrão | Efeito |
| --- | --- | --- |
| `--report` | nenhum | Relatório aberto ao carregar a página |
| `--host` | `127.0.0.1` | Endereço de escuta |
| `--port` | `8000` | Porta de escuta; `0` escolhe uma porta livre |

O servidor lê o arquivo a cada requisição, então recarregar a página mostra um
relatório gerado novamente. Um arquivo inválido na inicialização encerra o
comando com código `1`; depois de iniciado, o erro aparece na página.

## Decisões

- **Sem dependências e sem build.** O runtime continua restrito à biblioteca
  padrão. A interface usa HTML, CSS e módulos JavaScript empacotados em
  `src/ranklab/web/`.
- **O navegador não calcula as análises.** Os resultados vêm do JSON; o cliente
  apenas valida, formata e exibe, sem criar uma segunda implementação dos
  algoritmos.
- **Erro não vira resultado vazio.** Relatório inválido ou de outra versão
  substitui a tela por uma mensagem de erro, sem manter o relatório anterior.
- **Conteúdo do relatório é texto.** Valores do JSON nunca são interpretados
  como HTML, e o servidor envia uma política de segurança de conteúdo restritiva.

## Contrato HTTP

| Rota | Resposta |
| --- | --- |
| `GET /` e arquivos listados em `STATIC_FILES` (`src/ranklab/server.py`) | Interface |
| `GET /api/report` | `200` com o relatório |
| `GET /api/report` sem `--report` | `404` com `{"error": ...}` |
| `GET /api/report` com arquivo inválido | `422` com `{"error": ...}` |

Só os arquivos listados são servidos. Outros caminhos retornam `404`.

## Testes

```bash
python -m pytest -q tests/test_web_server.py
node --test tests/web/report.test.mjs
```

Os testes JavaScript exigem Node.js 22 ou superior apenas no desenvolvimento,
sem instalar pacotes.

## Limitações

- O visualizador lê apenas o formato 3 do relatório e não executa análises.
- O servidor não tem autenticação nem TLS. Ao usar `--host` com outro endereço,
  qualquer máquina que alcance a porta pode ler o relatório indicado.
- A coleção da seleção está no relatório, mas sua visualização ainda não existe.
