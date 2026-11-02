# Integração contínua e qualidade

O workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) reproduz o
caminho de um clone limpo descrito no README e falha quando a suíte de testes
ou a embalagem da interface falham.

## O que o CI executa

| Job | Conteúdo |
| --- | --- |
| `test` | Python 3.11 e a versão estável mais recente (`3.x`); `pytest`; comandos da demonstração do README, incluindo `serve`; `ruff check` informativo, sem reformatação em massa |
| `javascript` | `node --test` das funções do visualizador |
| `package` | Constrói a wheel, instala sem o código-fonte no caminho e confirma que todo arquivo de `STATIC_FILES` foi incluído |
| `browser` | Playwright + Chromium e a suíte em `tests/browser` |

Pull requests mostram o estado de cada job. Uma falha em testes deixa o
workflow vermelho.

## Avaliação do ruff

Com o `ruff` 0.17.1 e a configuração padrão, `ruff check src tests` aponta 19
achados, 18 deles corrigíveis automaticamente: 11 `I001` (ordem de imports),
2 `F401`, 2 `RUF100`, 2 `SIM114`, 1 `BLE001` e 1 `RUF022`. Nenhum indica defeito
de execução nos testes atuais.

A recomendação é manter o `ruff check` como passo informativo
(`continue-on-error`), que aparece como aviso sem deixar o workflow vermelho, e
não aplicar `ruff format` no código existente: a reformatação em massa geraria
conflitos com o trabalho em andamento sem ganho proporcional. Passar a bloquear
o CI é uma decisão do grupo, depois de corrigir esses achados. O `ruff` é
instalado apenas no CI e não entra no runtime.

## Testes de navegador

As ferramentas de navegador ficam no extra opcional `browser` e não entram no
runtime do RankLab. Comandos e critérios de acessibilidade estão em
[`docs/testes-navegador.md`](testes-navegador.md).
