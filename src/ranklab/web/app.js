import {
  ReportFormatError,
  describeDelta,
  directionLabel,
  formatNumber,
  formatShare,
  formatSignedNumber,
  orderingAnswer,
  percentileConversionText,
  proximityAnswer,
  selectionAnswer,
  selectionDisplayModel,
  sensitivityAnswer,
  validateReport,
} from "./report.js";

const content = document.querySelector("#content");
const index = document.querySelector("#index");
const reportName = document.querySelector("#report-name");
const fileInput = document.querySelector("#report-file");

const AUDIT_COMMAND =
  "python -m ranklab audit-report examples/matriz.json \\\n" +
  "  --first-ranking examples/ranking.json \\\n" +
  "  --second-ranking examples/ranking-operacional.json \\\n" +
  "  --base-weights examples/pesos.json \\\n" +
  "  --changed-weights examples/pesos-alterados-muda.json \\\n" +
  "  --closest-criteria qualidade prazo_dias \\\n" +
  "  --selection-criterion qualidade --percentile 50 \\\n" +
  "  --output relatorio.json";

// Textos do relatório vêm de arquivos do usuário: entram sempre como nós de
// texto, nunca como HTML.
function el(tag, attributes = {}, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  node.append(...children.filter((child) => child !== null && child !== undefined));
  return node;
}

function facts(entries) {
  return el(
    "dl",
    { class: "facts" },
    ...entries.flatMap(([term, description]) => [el("dt", {}, term), el("dd", {}, description)]),
  );
}

function table(caption, headers, rows) {
  const headerRow = el(
    "tr",
    {},
    ...headers.map((header) =>
      typeof header === "string"
        ? el("th", { scope: "col" }, header)
        : el("th", { scope: "col", class: header.class }, header.text),
    ),
  );
  const bodyRows = rows.map(([rowHeader, ...cells]) =>
    el("tr", {}, el("th", { scope: "row" }, rowHeader), ...cells.map((cell) => cellNode(cell))),
  );
  // Tabela mais larga que a tela rola sozinha; precisa de foco para rolar por teclado.
  return el(
    "div",
    { class: "table-scroll", tabindex: "0", role: "region", "aria-label": caption },
    el("table", {}, el("caption", {}, caption), el("thead", {}, headerRow), el("tbody", {}, ...bodyRows)),
  );
}

function cellNode(cell) {
  if (cell instanceof Node) return el("td", {}, cell);
  if (cell && typeof cell === "object") return el("td", { class: cell.class }, cell.text);
  return el("td", {}, String(cell));
}

function deltaNode(delta) {
  const { mark, text, tone } = describeDelta(delta);
  return el("span", { class: tone }, `${mark} ${text}`);
}

function section(id, title, question, answer, ...children) {
  return {
    id,
    title,
    node: el(
      "section",
      { class: "analysis", id, "aria-labelledby": `${id}-question` },
      el("h2", { id: `${id}-question` }, question),
      el("p", { class: "answer" }, answer),
      ...children,
    ),
  };
}

function rankingLabel({ name, origin, ranking_id: id }) {
  return `${name} (origem: ${origin}; ID: ${id})`;
}

function orderingSection(analysis) {
  const pairs = analysis.discordant_pairs;
  const pairsContent =
    pairs && pairs.length > 0
      ? el(
          "ul",
          {},
          ...pairs.map(({ earlier_in_first: earlier, later_in_first: later }) =>
            el("li", {}, `${earlier} vem antes de ${later} no primeiro ranking e depois no segundo.`),
          ),
        )
      : el("p", {}, pairs ? "Nenhum par discordante." : analysis.pair_explanation);

  return section(
    "divergencia",
    "Divergência de ordenação",
    analysis.question,
    orderingAnswer(analysis),
    facts([
      ["Primeiro ranking", rankingLabel(analysis.first)],
      ["Segundo ranking", rankingLabel(analysis.second)],
      ["Total de inversões", `${analysis.discordant_pair_count} de ${analysis.possible_pair_count} pares`],
      ["Distância de Kendall normalizada", formatNumber(analysis.kendall_normalized_distance)],
    ]),
    table(
      "Posições por item. Variação positiva significa subida no segundo ranking.",
      ["Item", "Primeiro", "Segundo", "Variação"],
      analysis.positions.map((item) => [
        item.item_id,
        item.first_position,
        item.second_position,
        deltaNode(item.position_delta),
      ]),
    ),
    el("h3", {}, "Pares discordantes"),
    pairsContent,
  );
}

function criterionDescription({ name, direction, unit }) {
  return `${name} (${unit}; ${directionLabel(direction)})`;
}

function proximitySection(analysis) {
  const criteria = analysis.criterion_definitions;
  return section(
    "proximidade",
    "Proximidade em atributos",
    analysis.question,
    proximityAnswer(analysis),
    el("p", { class: "note" }, analysis.interpretation),
    table(
      "Valores de origem do par nos critérios escolhidos.",
      ["Item", ...criteria.map(({ name, unit }) => `${name} (${unit})`)],
      analysis.item_ids.map((itemId) => [
        itemId,
        ...criteria.map(({ criterion_id: id }) => formatNumber(analysis.source_values[itemId][id])),
      ]),
    ),
    facts([
      ["Normalização", analysis.normalization],
      ["Métrica", analysis.metric],
      ["Critérios", criteria.map(criterionDescription).join("; ")],
    ]),
    el("h3", {}, "Limitações"),
    el("ul", {}, ...analysis.limitations.map((limitation) => el("li", {}, limitation))),
  );
}

function selectionSourceLabel(source) {
  if (source.type === "matrix_criterion") {
    return `Critério ${source.name} da matriz (${source.unit}; ID: ${source.criterion_id})`;
  }
  return `Lista JSON em ${source.path}`;
}

function selectionSection(analysis) {
  const { percentile } = analysis;
  const display = selectionDisplayModel(analysis);
  let strip;
  if (display.status === "available") {
    strip = el(
      "div",
      {
        class: "order-strip-scroll",
        tabindex: "0",
        role: "region",
        "aria-label": "Valores ordenados somente para exibição",
      },
      el(
        "ol",
        { class: "order-strip" },
        ...display.entries.map((entry) =>
          el(
            "li",
            entry.selected
              ? { class: "selected-order", "aria-current": "true" }
              : {},
            el("span", { class: "order-position" }, `k = ${entry.order}`),
            el("span", { class: "order-value" }, formatNumber(entry.value)),
          ),
        ),
      ),
    );
  } else if (display.status === "omitted") {
    strip = el(
      "p",
      { class: "note" },
      `${display.reason ?? "Coleção omitida."} ` +
        `${display.itemCount} valores; limite de exibição: ${display.limit}.`,
    );
  } else {
    strip = el(
      "p",
      { class: "note" },
      "Este relatório não contém a coleção necessária para desenhar a faixa.",
    );
  }
  const conversion = percentileConversionText(analysis);
  return section(
    "selecao",
    "Seleção de ordem",
    analysis.question,
    selectionAnswer(analysis),
    facts([
      ["Origem dos valores", selectionSourceLabel(analysis.source)],
      ["Tamanho da coleção", String(analysis.source.item_count)],
      ["Ordem", `k = ${analysis.order}`],
      ["Percentil", percentile === null || percentile === undefined ? "não informado" : formatNumber(percentile)],
      ["Valor selecionado", analysis.source.unit ? `${formatNumber(analysis.value)} ${analysis.source.unit}` : formatNumber(analysis.value)],
    ]),
    conversion === null
      ? null
      : el("p", { class: "percentile-conversion" }, "Conversão do percentil: ", el("code", {}, conversion)),
    strip,
    el(
      "p",
      { class: "note" },
      "Esta ordenação existe somente para exibição. O algoritmo encontra o elemento de ordem k sem ordenar toda a coleção, e o resultado não é um ranking agregado.",
    ),
  );
}

function crossingsLabel(crossings) {
  if (crossings === null) return "omitidos pelo limite de itens";
  return crossings.length > 0 ? crossings.join(", ") : "nenhum";
}

function weightRows(analysis, criteria) {
  const changedWeights = new Map(analysis.changed.weights.map((weight) => [weight.criterion_id, weight]));
  return analysis.base.weights.map((weight) => {
    const changed = changedWeights.get(weight.criterion_id);
    return [
      criteria.get(weight.criterion_id)?.name ?? weight.criterion_id,
      `${formatNumber(weight.input)} (${formatShare(weight.normalized)})`,
      `${formatNumber(changed.input)} (${formatShare(changed.normalized)})`,
    ];
  });
}

function normalizedValuesTable(scenario, caption, criteria) {
  const ids = scenario.weights.map((weight) => weight.criterion_id);
  return table(
    caption,
    ["Posição e item", ...ids.map((id) => criteria.get(id)?.name ?? id), "Score"],
    scenario.items.map((item) => [
      `${item.position}. ${item.item_id}`,
      ...ids.map((id) => formatNumber(item.normalized_values[id])),
      formatNumber(item.score),
    ]),
  );
}

function sensitivitySection(analysis, criteria) {
  const divergence = analysis.ranking_divergence;
  return section(
    "sensibilidade",
    "Sensibilidade aos pesos",
    analysis.question,
    sensitivityAnswer(analysis),
    table(
      "Pesos de entrada de cada cenário, com a participação normalizada entre parênteses.",
      ["Critério", "Base", "Alterado"],
      weightRows(analysis, criteria),
    ),
    table(
      "Comparação por item. Variação positiva significa subida no cenário alterado.",
      ["Item", "Posição base", "Posição alterada", "Variação", "Score base", "Score alterado", "Variação do score", { class: "text-cell", text: "Cruzou com" }],
      analysis.items.map((item) => [
        item.item_id,
        item.base_position,
        item.changed_position,
        deltaNode(item.position_delta),
        formatNumber(item.base_score),
        formatNumber(item.changed_score),
        formatSignedNumber(item.score_delta),
        { class: "text-cell", text: crossingsLabel(item.crossed_item_ids) },
      ]),
    ),
    facts([
      ["Total de inversões entre cenários", `${divergence.discordant_pair_count} de ${divergence.possible_pair_count} pares`],
      ["Distância de Kendall normalizada", formatNumber(divergence.kendall_normalized_distance)],
      ["Normalização", analysis.base.normalization],
      ["Agregação", analysis.base.aggregation],
      ["Desempate", analysis.base.tie_break],
    ]),
    el(
      "details",
      {},
      el("summary", {}, "Valores normalizados usados no score"),
      normalizedValuesTable(analysis.base, "Cenário base", criteria),
      normalizedValuesTable(analysis.changed, "Cenário alterado", criteria),
    ),
  );
}

function inputsSection(report) {
  const { inputs, matrix } = report;
  return section(
    "entradas",
    "Entradas e limites",
    "Com quais dados e limites este relatório foi gerado?",
    `${matrix.name}, com ${matrix.criteria.length} critérios. Origem declarada: ${matrix.origin}.`,
    facts([
      ["Matriz", inputs.matrix],
      ["Primeiro ranking", inputs.first_ranking],
      ["Segundo ranking", inputs.second_ranking],
      ["Pesos base", inputs.base_weights],
      ["Pesos alterados", inputs.changed_weights],
    ]),
    table(
      "Critérios da matriz.",
      ["Critério", "ID", "Unidade", "Direção"],
      matrix.criteria.map((criterion) => [
        criterion.name,
        criterion.criterion_id,
        criterion.unit,
        directionLabel(criterion.direction),
      ]),
    ),
    el("h3", {}, "Limites da análise"),
    el(
      "ul",
      {},
      el("li", {}, "Nenhuma dessas medidas, isoladamente, determina qual decisão é a correta."),
      el("li", {}, "A comparação aceita apenas rankings estritos dos mesmos itens."),
      el("li", {}, "A soma ponderada é compensatória e a normalização min-max é sensível aos extremos."),
      el("li", {}, "Os números são arredondados para exibição; o JSON preserva a precisão calculada."),
    ),
  );
}

function clearReport() {
  index.hidden = true;
  index.replaceChildren();
  reportName.textContent = "Relatório auditável";
}

function showState(title, ...children) {
  clearReport();
  content.replaceChildren(el("div", { class: "state" }, el("h1", {}, title), ...children));
}

function showLoading(source) {
  showState("Carregando relatório", el("p", {}, source));
}

function showEmpty() {
  showState(
    "Abra um relatório para começar",
    el("p", {}, "Escolha um JSON gerado pelo RankLab em “Abrir relatório”. Para criar um com os dados de exemplo, execute na raiz do projeto:"),
    el("pre", { tabindex: "0" }, el("code", {}, AUDIT_COMMAND)),
    el("p", {}, "Para abri-lo direto ao iniciar: ", el("code", {}, "python -m ranklab serve --report relatorio.json")),
  );
}

function showError(title, detail, nextStep) {
  showState(
    title,
    el("p", { class: "error-detail", role: "alert" }, detail),
    el("p", {}, nextStep),
  );
}

function renderReport(report, sourceLabel) {
  const { analyses, matrix } = report;
  const criteria = new Map(matrix.criteria.map((criterion) => [criterion.criterion_id, criterion]));
  const sections = [
    orderingSection(analyses.ordering_divergence),
    proximitySection(analyses.proximity),
    selectionSection(analyses.order_selection),
    sensitivitySection(analyses.weight_sensitivity, criteria),
    inputsSection(report),
  ];

  // Só substitui a tela depois de montar tudo: falha na montagem não deixa seção parcial.
  index.replaceChildren(...sections.map(({ id, title }) => el("a", { href: `#${id}` }, title)));
  index.hidden = false;
  reportName.textContent = `${matrix.name} (${sourceLabel})`;
  content.replaceChildren(
    el("h1", { class: "visually-hidden" }, `Relatório auditável: ${matrix.name}`),
    ...sections.map(({ node }) => node),
  );
}

function presentReport(data, sourceLabel, nextStep) {
  try {
    renderReport(validateReport(data), sourceLabel);
  } catch (error) {
    // TypeError aqui indica campo aninhado fora do contrato; não vira tela em branco.
    const detail = error instanceof ReportFormatError ? error.message : `A estrutura do relatório é inválida: ${error.message}`;
    showError("Não foi possível exibir o relatório", detail, nextStep);
  }
}

// Evita que uma resposta antiga do servidor substitua o arquivo escolhido depois.
let latestLoad = 0;

async function loadFromServer() {
  const load = ++latestLoad;
  showLoading("Buscando o relatório indicado ao servidor.");
  const nextStep = "Corrija o arquivo, gere o relatório novamente ou escolha outro em “Abrir relatório”.";
  try {
    const response = await fetch("api/report", { headers: { Accept: "application/json" } });
    if (load !== latestLoad) return;
    if (response.status === 404) {
      showEmpty();
      return;
    }
    const data = await response.json();
    if (load !== latestLoad) return;
    if (!response.ok) {
      showError("Não foi possível carregar o relatório", data.error, nextStep);
      return;
    }
    presentReport(data, "indicado no servidor", nextStep);
  } catch (error) {
    if (load !== latestLoad) return;
    showError(
      "Não foi possível falar com o servidor",
      error.message,
      "Confira se python -m ranklab serve está em execução ou escolha um arquivo em “Abrir relatório”.",
    );
  }
}

async function loadFromFile(file) {
  const load = ++latestLoad;
  showLoading(`Lendo ${file.name}.`);
  const nextStep = "Escolha outro arquivo em “Abrir relatório”.";
  let text;
  try {
    text = await file.text();
  } catch (error) {
    if (load === latestLoad) showError(`Não foi possível ler ${file.name}`, error.message, nextStep);
    return;
  }
  if (load !== latestLoad) return;
  let data;
  try {
    data = JSON.parse(text);
  } catch (error) {
    showError(`${file.name} não é um JSON válido`, error.message, nextStep);
    return;
  }
  presentReport(data, file.name, nextStep);
}

fileInput.addEventListener("change", () => {
  const [file] = fileInput.files;
  if (!file) return;
  loadFromFile(file);
  // Permite escolher o mesmo arquivo de novo depois de corrigi-lo.
  fileInput.value = "";
});

loadFromServer();
