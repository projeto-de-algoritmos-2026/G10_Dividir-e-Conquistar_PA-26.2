# Roteiro de apresentação — RankLab

Roteiro sugerido para uma demonstração de 8 a 10 minutos. Execute os comandos
a partir da raiz do repositório, após a instalação descrita no README.

## 1. Aplicação e problema — 1 minuto

**Mensagem:** rankings e decisões multicritério podem mudar quando a fonte, os
atributos ou os pesos mudam. O RankLab torna essas mudanças visíveis e
auditáveis.

Apresente o cenário fictício de três fornecedores e deixe explícito que os
dados são sintéticos, licenciados sob MIT e não representam empresas reais.
Mostre rapidamente [`../examples/README.md`](../examples/README.md).

## 2. Entradas e contratos — 1 minuto

```bash
python -m ranklab load-matrix examples/matriz.json
python -m ranklab load-ranking examples/ranking.json
python -m ranklab load-ranking examples/ranking-operacional.json
```

Explique que os rankings são completos, estritos e usam os mesmos IDs. A
matriz tem qualidade, em que maior é melhor, e prazo em dias, em que menor é
melhor. A validação rejeita lacunas, duplicatas, valores ausentes e tipos
inválidos em vez de corrigi-los silenciosamente.

## 3. Demonstração das análises — 3 minutos

### Comparação por inversões

```bash
python -m ranklab compare-rankings examples/ranking.json examples/ranking-operacional.json
```

Resultado a destacar: `fornecedor-a` e `fornecedor-b` trocam de ordem. Há uma
inversão entre três pares e distância de Kendall normalizada `0,333333`.

### Par mais próximo

```bash
python -m ranklab closest-pair examples/matriz.json qualidade prazo_dias
```

Resultado: `fornecedor-a` e `fornecedor-c`. A distância é calculada depois da
normalização das escalas e só significa proximidade nos dois atributos
escolhidos.

### Seleção de ordem

```bash
python -m ranklab select examples/valores-qualidade.json --percentile 50
```

Resultado: `90` pontos, ordem `k=2`. Ressalte que o algoritmo encontra a ordem
estatística sem transformar a coleção em um ranking agregado.

### Sensibilidade aos pesos

```bash
python -m ranklab compare-weights examples/matriz.json --base-weights examples/pesos.json --changed-weights examples/pesos-alterados-muda.json
```

Resultado: ao aumentar a importância do prazo, `fornecedor-b` ultrapassa
`fornecedor-a`. A ferramenta mostra pesos normalizados, scores, posições,
cruzamentos e divergência entre os rankings.

## 4. Fluxo integrado — 1 minuto

```bash
python -m ranklab audit-report examples/matriz.json --first-ranking examples/ranking.json --second-ranking examples/ranking-operacional.json --base-weights examples/pesos.json --changed-weights examples/pesos-alterados-muda.json --closest-criteria qualidade prazo_dias --selection-criterion qualidade --percentile 50
```

Mostre as quatro chaves de `analyses` no JSON: `ordering_divergence`,
`proximity`, `order_selection` e `weight_sensitivity`. Explique que o relatório
preserva arquivos, parâmetros, unidades, normalização, métrica e regras de
desempate para permitir reprodução e auditoria.

## 5. Implementação de dividir e conquistar — 1 minuto

- **Inversões:** transforma o segundo ranking em posições e conta inversões
  durante o merge sort.
- **Seleção:** usa mediana das medianas como pivô, particiona em menores,
  iguais e maiores e recorre somente na faixa que contém a ordem desejada.
- **Par mais próximo:** divide os pontos ordenados por `x`, resolve as metades
  e examina uma faixa central ordenada por `y`.

Não misture este bloco com evidências de corretude ou tempos medidos: aqui a
pergunta é como o código foi estruturado.

## 6. Corretude — 1 minuto

Apresente os invariantes resumidos:

- o merge devolve cada trecho ordenado e conta cada inversão exatamente uma
  vez;
- as partições da seleção são disjuntas, cobrem a entrada e preservam a ordem
  estatística procurada;
- todo par está na esquerda, direita ou faixa central, e a ordenação por `y`
  limita os vizinhos necessários.

Informe que testes determinísticos comparam os resultados a oráculos simples
em entradas pequenas. As provas e os testes são evidências complementares,
não equivalentes.

## 7. Complexidade e desempenho — 1 minuto

| Algoritmo | Tempo | Espaço auxiliar |
| --- | --- | --- |
| Inversões | `O(n log n)` | `O(n)` |
| Seleção determinística | `O(n)` no pior caso | `O(n)` |
| Par mais próximo | `O(n log n)` | `O(n)` |

Use [`corretude-e-desempenho.md`](corretude-e-desempenho.md) para mostrar que
os oráculos quadráticos crescem mais rapidamente. Ressalte que `sorted` pode
ser mais rápido que a seleção em tamanhos pequenos por ser implementado em
código nativo; isso não altera a análise assintótica.

## 8. Limitações e encerramento — 1 minuto

- rankings precisam ser completos, estritos e sem empates;
- a matriz aceita apenas valores quantitativos completos;
- proximidade usa exatamente duas dimensões, min-max e distância Euclidiana;
- min-max é sensível a extremos e soma ponderada permite compensações;
- o MVP usa CLI e JSON, sem interface gráfica ou persistência;
- os dados são fictícios e servem somente à demonstração acadêmica;
- benchmarks dependem do ambiente e não provam complexidade.

**Encerramento:** o RankLab não decide qual fornecedor é correto. Ele torna
explícitas as entradas, regras e mudanças que levaram a cada resultado.

## Checklist antes de apresentar

1. Criar e ativar o ambiente virtual.
2. Executar `python -m pip install -e ".[dev]"`.
3. Executar `python -m pytest -q`.
4. Testar o comando integrado e os quatro comandos individuais.
5. Manter este roteiro e os resultados de referência abertos como contingência.
