# Visualizador web

O comando `serve` permite gerar ou abrir no navegador o relatório de
`audit-report`. Cada
análise aparece em uma seção própria, com sua pergunta, resposta, evidências e
parâmetros, seguindo a separação descrita em
[`relatorio-auditavel.md`](relatorio-auditavel.md).

## Uso

```bash
python -m ranklab audit-report examples/matriz.json --first-ranking examples/ranking.json --second-ranking examples/ranking-operacional.json --base-weights examples/pesos.json --changed-weights examples/pesos-alterados-muda.json --closest-criteria qualidade prazo_dias --selection-criterion qualidade --percentile 50 --output relatorio.json
python -m ranklab serve --report relatorio.json
```

Acesse o endereço impresso pelo comando. O formulário aceita matriz, rankings,
pesos, critérios de proximidade e ordem de seleção. "Carregar demonstração"
preenche as entradas de `examples/`; após uma execução válida, o relatório
pode ser baixado em JSON ou exportado para PDF. Sem `--report`, a página
continua permitindo abrir um relatório pronto.

Para exportar o PDF, gere ou abra um relatório e clique em **Exportar PDF**.
Na janela de impressão, escolha **Salvar como PDF**. O documento inclui um
resumo executivo, métricas, gráficos de posições e scores, além das tabelas e
evidências das análises. O botão **Baixar JSON** continua disponível para
integração técnica e auditoria automatizada.

Para entregar um único arquivo que não depende de Python, servidor ou rede,
adicione `--html-output` ao comando:

```bash
python -m ranklab audit-report examples/matriz.json --first-ranking examples/ranking.json --second-ranking examples/ranking-operacional.json --base-weights examples/pesos.json --changed-weights examples/pesos-alterados-muda.json --closest-criteria qualidade prazo_dias --selection-criterion qualidade --percentile 50 --output relatorio.json --html-output relatorio.html
```

O arquivo `relatorio.html` pode ser aberto diretamente via `file://`. Ele
contém o CSS, o JavaScript e os dados do relatório embutidos, e inclui regras
específicas para impressão.

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
- **Pesos são recalculados no servidor.** Os controles mostram o valor de
  entrada e o normalizado devolvido por `compare_weight_scenarios`. Requisições
  antigas são canceladas e ignoradas se uma alteração mais recente existir.
- **Erro não vira resultado vazio.** Relatório inválido ou de outra versão
  substitui a tela por uma mensagem de erro, sem manter o relatório anterior.
- **Conteúdo do relatório é texto.** Valores do JSON nunca são interpretados
  como HTML, e o servidor envia uma política de segurança de conteúdo restritiva.
- **Entrega offline.** O HTML standalone reutiliza o mesmo visualizador, mas
  não referencia arquivos externos nem precisa acessar a rede.

## Contrato HTTP

| Rota | Resposta |
| --- | --- |
| `GET /` e arquivos listados em `STATIC_FILES` (`src/ranklab/server.py`) | Interface |
| `GET /api/report` | `200` com o relatório |
| `GET /api/report` sem `--report` | `404` com `{"error": ...}` |
| `GET /api/report` com arquivo inválido | `422` com `{"error": ...}` |
| `POST /api/report` | `200` com um relatório gerado a partir dos documentos enviados |
| `GET /api/examples/audit-report` | Documentos da demonstração no formato de requisição |
| `POST /api/weight-sensitivity` | Comparação do cenário base com os pesos ajustados |

O contrato completo do `POST`, seus erros e o limite de 1 MiB estão em
[`api-local.md`](api-local.md).

Só os arquivos listados são servidos. Outros caminhos retornam `404`.

## Testes

```bash
python -m pytest -q tests/test_web_server.py
node --test tests/web/report.test.mjs
node --test tests/web/form.test.mjs
```

Os testes JavaScript exigem Node.js 22 ou superior apenas no desenvolvimento,
sem instalar pacotes.

## Limitações

- O visualizador lê apenas o formato 2 do relatório; os cálculos são executados
  pela API local, não por JavaScript.
- O servidor não tem autenticação nem TLS. Ao usar `--host` com outro endereço,
  qualquer máquina que alcance a porta pode ler o relatório indicado.
- O relatório não traz todos os pontos da matriz. A coleção da seleção é
  incluída somente até 100 valores para desenhar a faixa de ordem.
- Rastreamentos também são materializados somente até 100 itens.
