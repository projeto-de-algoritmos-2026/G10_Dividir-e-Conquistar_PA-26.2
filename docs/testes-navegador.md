# Testes de navegador e acessibilidade

Ferramentas restritas ao ambiente de desenvolvimento. O runtime do RankLab
continua sem dependências externas; Playwright e Chromium entram apenas pelo
extra opcional `[browser]`.

## Instalação

```bash
python -m pip install -e ".[browser]"
python -m playwright install chromium
```

Em CI o workflow já instala as dependências de sistema do Chromium.

## Comando

A partir da raiz do repositório:

```bash
python -m pytest -q tests/browser
```

A suíte cobre:

- relatório válido indicado ao servidor;
- relatório inválido;
- ausência de relatório;
- troca de arquivo pelo seletor “Abrir relatório”, nos dois sentidos;
- relatório do conjunto ampliado, que declara os dados como sintéticos;
- navegação por teclado: skip link até o conteúdo e `Tab` até os controles
  principais;
- largura de celular (390×844), sem transbordo horizontal da página;
- auditoria axe-core nos temas claro e escuro (`prefers-color-scheme`), exigindo
  que o contraste tenha sido medido;
- controle negativo: a auditoria reprova texto de baixo contraste injetado.

Sem Playwright instalado, os testes desta pasta são pulados por
`python -m pytest -q`. Com Playwright e sem Chromium, eles falham até o segundo
comando de instalação ser executado.

O motor axe está vendored em `tests/browser/vendor/axe.min.js` (axe-core 4.10.2)
para não depender de rede nem relaxar a Content-Security-Policy da página.

## Critério de acessibilidade

Qualquer violação `critical` ou `serious` sem justificativa registrada falha o
teste. Justificativas aceitas devem ser listadas abaixo e espelhadas em
`ALLOWED_SERIOUS_IDS` em `tests/browser/test_accessibility.py`.

### Justificativas registradas

Nenhuma violação crítica ou séria está liberada neste momento.

## Limitações

- Os testes usam Chromium headless; não substituem revisão manual em Firefox ou
  leitores de tela.
- Contraste é verificado pelo axe nos dois esquemas de cor; diferenças sutis de
  tipografia em monitores calibrados podem exigir checagem humana.
