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
import {
  buildReportPayload,
  buildSensitivityPayload,
  criteriaFromMatrix,
  validateSensitivityResponse,
  weightsFromAnalysis,
} from "./form.js";

const content = document.querySelector("#content");
const index = document.querySelector("#index");
const reportName = document.querySelector("#report-name");
const fileInput = document.querySelector("#report-file");
const analysisForm = document.querySelector("#analysis-form");
const loadExampleButton = document.querySelector("#load-example");
const downloadReport = document.querySelector("#download-report");
const formStatus = document.querySelector("#form-status");
const formErrorSummary = document.querySelector("#form-error-summary");
const weightEditor = document.querySelector("#weight-editor");
const weightForm = document.querySelector("#weight-form");
const weightFields = document.querySelector("#weight-fields");
const weightStatus = document.querySelector("#weight-status");
const weightError = document.querySelector("#weight-error");

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

function traceValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return formatNumber(value);
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

function tracePlayer(trace, title) {
  if (!trace) return null;
  if (trace.status === "omitted" || !Array.isArray(trace.steps)) {
    return el(
      "section",
      { class: "trace-panel", "aria-label": title },
      el("h3", {}, title),
      el(
        "p",
        { class: "note" },
        `${trace.reason ?? "Rastreamento omitido."} ${trace.item_count} itens; limite: ${trace.limit}.`,
      ),
    );
  }
  if (trace.steps.length === 0) return null;

  const description = el("p", { class: "trace-description", "aria-live": "polite" });
  const progress = el("span", { class: "trace-progress" });
  const state = el("dl", { class: "trace-state" });
  const previous = el("button", { type: "button", class: "secondary-button" }, "Voltar");
  const next = el("button", { type: "button", class: "secondary-button" }, "Avançar");
  const play = el("button", { type: "button", class: "secondary-button" }, "Reproduzir");
  let current = 0;
  let timer = null;

  const render = () => {
    const step = trace.steps[current];
    progress.textContent = `Passo ${current + 1} de ${trace.steps.length}`;
    description.textContent = step.description;
    state.replaceChildren(
      ...Object.entries(step.state).flatMap(([key, value]) => [
        el("dt", {}, key.replaceAll("_", " ")),
        el("dd", {}, el("pre", { tabindex: "0" }, traceValue(value))),
      ]),
    );
    previous.disabled = current === 0;
    next.disabled = current === trace.steps.length - 1;
    if (next.disabled && timer !== null) {
      window.clearInterval(timer);
      timer = null;
      play.textContent = "Reproduzir";
    }
  };
  previous.addEventListener("click", () => {
    current = Math.max(0, current - 1);
    render();
  });
  next.addEventListener("click", () => {
    current = Math.min(trace.steps.length - 1, current + 1);
    render();
  });
  play.addEventListener("click", () => {
    if (timer !== null) {
      window.clearInterval(timer);
      timer = null;
      play.textContent = "Reproduzir";
      return;
    }
    if (current === trace.steps.length - 1) current = 0;
    play.textContent = "Pausar";
    render();
    timer = window.setInterval(() => {
      current = Math.min(trace.steps.length - 1, current + 1);
      render();
    }, window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 1400 : 900);
  });

  const tree = el(
    "ol",
    { class: "trace-tree", "aria-label": "Árvore e fases da execução" },
    ...trace.steps.map((step) =>
      el(
        "li",
        { class: `trace-depth-${Math.min(step.depth, 6)}` },
        el("span", { class: "trace-kind" }, step.kind),
        ` ${step.description}`,
      ),
    ),
  );
  const panel = el(
    "section",
    { class: "trace-panel", "aria-label": title },
    el("h3", {}, title),
    tree,
    el("div", { class: "trace-controls" }, previous, play, next, progress),
    description,
    state,
  );
  render();
  return panel;
}

function rankingLabel({ name, origin, ranking_id: id }) {
  return `${name} (origem: ${origin}; ID: ${id})`;
}

function orderingSection(analysis, trace = null) {
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
    tracePlayer(trace, "Passo a passo do merge sort"),
  );
}

function criterionDescription({ name, direction, unit }) {
  return `${name} (${unit}; ${directionLabel(direction)})`;
}

function proximitySection(analysis, trace = null) {
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
    tracePlayer(trace, "Passo a passo do par mais próximo"),
  );
}

function selectionSourceLabel(source) {
  if (source.type === "matrix_criterion") {
    return `Critério ${source.name} da matriz (${source.unit}; ID: ${source.criterion_id})`;
  }
  return `Lista JSON em ${source.path}`;
}

function selectionSection(analysis, trace = null) {
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
    tracePlayer(trace, "Passo a passo da mediana das medianas"),
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
  const traces = report.traces ?? {};
  const criteria = new Map(matrix.criteria.map((criterion) => [criterion.criterion_id, criterion]));
  const sections = [
    orderingSection(analyses.ordering_divergence, traces.ordering_divergence),
    proximitySection(analyses.proximity, traces.proximity),
    selectionSection(analyses.order_selection, traces.order_selection),
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

let currentReport = null;
let reportObjectUrl = null;

function updateDownload(report) {
  if (reportObjectUrl !== null) URL.revokeObjectURL(reportObjectUrl);
  reportObjectUrl = null;
  downloadReport.hidden = true;
  downloadReport.removeAttribute("href");
  if (!report) return;
  const blob = new Blob([`${JSON.stringify(report, null, 2)}\n`], { type: "application/json" });
  reportObjectUrl = URL.createObjectURL(blob);
  downloadReport.href = reportObjectUrl;
  downloadReport.hidden = false;
}

function presentReport(data, sourceLabel, nextStep) {
  try {
    const report = validateReport(data);
    renderReport(report, sourceLabel);
    currentReport = report;
    updateDownload(report);
    return true;
  } catch (error) {
    // TypeError aqui indica campo aninhado fora do contrato; não vira tela em branco.
    const detail = error instanceof ReportFormatError ? error.message : `A estrutura do relatório é inválida: ${error.message}`;
    currentReport = null;
    updateDownload(null);
    showError("Não foi possível exibir o relatório", detail, nextStep);
    return false;
  }
}

// Evita que uma resposta antiga do servidor substitua o arquivo escolhido depois.
let latestLoad = 0;

async function loadFromServer() {
  const load = ++latestLoad;
  currentReport = null;
  updateDownload(null);
  weightEditor.hidden = true;
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
      showError("Não foi possível carregar o relatório", data.error?.message ?? data.error, nextStep);
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
  currentReport = null;
  updateDownload(null);
  weightEditor.hidden = true;
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

const documentFields = {
  matrix: ["matrix-file", "matrix-source"],
  first_ranking: ["first-ranking-file", "first-ranking-source"],
  second_ranking: ["second-ranking-file", "second-ranking-source"],
  base_weights: ["base-weights-file", "base-weights-source"],
  changed_weights: ["changed-weights-file", "changed-weights-source"],
  selection_values: ["selection-values-file", "selection-values-source"],
};
const fieldErrors = {
  matrix: "matrix-error",
  first_ranking: "first-ranking-error",
  second_ranking: "second-ranking-error",
  base_weights: "base-weights-error",
  changed_weights: "changed-weights-error",
  selection_values: "selection-values-error",
  closest_criteria: "closest-criteria-error",
  selection: "selection-error",
};
const analysisDocuments = {};
let analysisController = null;
let latestAnalysis = 0;

function clearFormErrors() {
  for (const id of Object.values(fieldErrors)) {
    const node = document.querySelector(`#${id}`);
    node.hidden = true;
    node.textContent = "";
  }
  formErrorSummary.hidden = true;
  formErrorSummary.textContent = "";
}

function showFieldError(key, message) {
  const id = fieldErrors[key];
  if (!id) return false;
  const node = document.querySelector(`#${id}`);
  node.textContent = message;
  node.hidden = false;
  return true;
}

function showFormError(error) {
  const message = error?.message ?? "Não foi possível gerar o relatório.";
  const placed = showFieldError(error?.input, message);
  formErrorSummary.textContent = error?.field_path
    ? `${message} Campo no JSON: ${error.field_path}.`
    : message;
  formErrorSummary.hidden = false;
  formErrorSummary.focus();
  if (placed) {
    const container = document.querySelector(`[data-error-for="${error.input}"]`);
    container?.querySelector("input, select, button")?.focus();
  }
}

function setCriteriaOptions(criteria, preferred = {}) {
  for (const [id, fallbackIndex] of [
    ["closest-first", 0],
    ["closest-second", 1],
    ["selection-criterion", 0],
  ]) {
    const select = document.querySelector(`#${id}`);
    select.replaceChildren(
      ...criteria.map((criterion) =>
        el(
          "option",
          { value: criterion.criterion_id },
          `${criterion.name}${criterion.unit ? ` (${criterion.unit})` : ""}`,
        ),
      ),
    );
    select.disabled = false;
    select.value = preferred[id] ?? criteria[fallbackIndex]?.criterion_id ?? "";
  }
}

function updateMatrixCriteria(content, preferred = {}) {
  try {
    setCriteriaOptions(criteriaFromMatrix(content), preferred);
    const error = document.querySelector("#matrix-error");
    error.hidden = true;
    error.textContent = "";
  } catch (error) {
    for (const id of ["closest-first", "closest-second", "selection-criterion"]) {
      const select = document.querySelector(`#${id}`);
      select.disabled = true;
      select.replaceChildren(el("option", { value: "" }, "Corrija a matriz"));
    }
    showFieldError("matrix", error.message);
  }
}

function setDocument(key, value) {
  analysisDocuments[key] = value;
  const [, sourceId] = documentFields[key];
  document.querySelector(`#${sourceId}`).textContent = value.source;
  if (key === "matrix") updateMatrixCriteria(value.content);
}

for (const [key, [inputId]] of Object.entries(documentFields)) {
  const input = document.querySelector(`#${inputId}`);
  input.addEventListener("change", async () => {
    const [file] = input.files;
    if (!file) return;
    try {
      setDocument(key, { source: file.name, content: await file.text() });
      const errorId = fieldErrors[key];
      if (errorId) document.querySelector(`#${errorId}`).hidden = true;
    } catch (error) {
      showFieldError(key, `Não foi possível ler ${file.name}: ${error.message}`);
    }
  });
}

function syncSelectionControls() {
  const source = analysisForm.elements["selection-source"].value;
  const useList = source === "json_list";
  document.querySelector("#selection-criterion-field").hidden = useList;
  document.querySelector("#selection-values-field").hidden = !useList;
  document.querySelector("#selection-values-file").required = useList;
  document.querySelector("#selection-criterion").required = !useList;
  const order = analysisForm.elements["selection-order"].value;
  document.querySelector("#selection-k").disabled = order !== "k";
  document.querySelector("#selection-percentile").disabled = order !== "percentile";
}

for (const input of analysisForm.querySelectorAll("input[name='selection-source'], input[name='selection-order']")) {
  input.addEventListener("change", syncSelectionControls);
}
syncSelectionControls();

loadExampleButton.addEventListener("click", async () => {
  clearFormErrors();
  loadExampleButton.disabled = true;
  formStatus.textContent = "Carregando demonstração…";
  try {
    const response = await fetch("api/examples/audit-report", { headers: { Accept: "application/json" } });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error?.message ?? "Exemplos indisponíveis.");
    for (const [key, value] of Object.entries(data.inputs)) setDocument(key, value);
    const parameters = data.parameters;
    setCriteriaOptions(criteriaFromMatrix(data.inputs.matrix.content), {
      "closest-first": parameters.closest_criteria[0],
      "closest-second": parameters.closest_criteria[1],
      "selection-criterion": parameters.selection.source.criterion_id,
    });
    analysisForm.elements["selection-source"].value = parameters.selection.source.type;
    analysisForm.elements["selection-order"].value = "percentile" in parameters.selection ? "percentile" : "k";
    document.querySelector("#selection-percentile").value = parameters.selection.percentile ?? 50;
    document.querySelector("#selection-k").value = parameters.selection.k ?? 1;
    syncSelectionControls();
    formStatus.textContent = "Demonstração pronta para executar.";
  } catch (error) {
    showFormError({ message: error.message });
    formStatus.textContent = "";
  } finally {
    loadExampleButton.disabled = false;
  }
});

function reportParameters() {
  const selectionSource = analysisForm.elements["selection-source"].value;
  const orderType = analysisForm.elements["selection-order"].value;
  const orderInput = document.querySelector(orderType === "k" ? "#selection-k" : "#selection-percentile");
  return {
    closestCriteria: [
      document.querySelector("#closest-first").value,
      document.querySelector("#closest-second").value,
    ],
    selectionSource,
    selectionCriterion: document.querySelector("#selection-criterion").value,
    orderType,
    orderValue: orderInput.valueAsNumber,
    includeTraces: document.querySelector("#include-traces").checked,
  };
}

function requireDocuments(parameters) {
  const required = ["matrix", "first_ranking", "second_ranking", "base_weights", "changed_weights"];
  if (parameters.selectionSource === "json_list") required.push("selection_values");
  let firstMissing = null;
  for (const key of required) {
    if (!analysisDocuments[key]) {
      showFieldError(key, "Escolha este arquivo.");
      firstMissing ??= key;
    }
  }
  if (firstMissing) {
    const inputId = documentFields[firstMissing][0];
    document.querySelector(`#${inputId}`).focus();
    throw new Error("Preencha todos os arquivos obrigatórios.");
  }
  if (!Number.isFinite(parameters.orderValue)) {
    showFieldError("selection", "Informe uma ordem ou percentil válido.");
    throw new Error("Informe uma ordem ou percentil válido.");
  }
}

analysisForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFormErrors();
  ++latestLoad;
  currentReport = null;
  updateDownload(null);
  weightEditor.hidden = true;
  clearReport();
  const parameters = reportParameters();
  try {
    requireDocuments(parameters);
  } catch (error) {
    formErrorSummary.textContent = error.message;
    formErrorSummary.hidden = false;
    showError("A análise não foi iniciada", error.message, "Preencha os campos indicados e tente novamente.");
    return;
  }

  const requestId = ++latestAnalysis;
  if (analysisController) analysisController.abort();
  analysisController = new AbortController();
  showLoading("Executando as análises no servidor local.");
  formStatus.textContent = "Gerando relatório…";
  document.querySelector("#generate-report").disabled = true;
  try {
    const payload = buildReportPayload(analysisDocuments, parameters);
    const response = await fetch("api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
      signal: analysisController.signal,
    });
    const data = await response.json();
    if (requestId !== latestAnalysis) return;
    if (!response.ok) {
      showFormError(data.error);
      showError("A análise não foi concluída", data.error?.message ?? "Entrada inválida.", "Corrija os campos indicados e tente novamente.");
      formStatus.textContent = "Falha na análise.";
      return;
    }
    if (presentReport(data, "gerado no navegador", "Corrija as entradas e tente novamente.")) {
      formStatus.textContent = "Relatório gerado.";
      setupWeightEditor();
    }
  } catch (error) {
    if (error.name === "AbortError" || requestId !== latestAnalysis) return;
    showFormError({ message: error.message });
    showError("Não foi possível falar com o servidor", error.message, "Confira se o servidor RankLab continua em execução.");
    formStatus.textContent = "Falha na análise.";
  } finally {
    if (requestId === latestAnalysis) document.querySelector("#generate-report").disabled = false;
  }
});

let sensitivityController = null;
let latestSensitivity = 0;
let sensitivityTimer = null;
let lastAcceptedWeights = null;

function readWeightControls() {
  return Object.fromEntries(
    [...weightFields.querySelectorAll("input[data-criterion]")].map((input) => [
      input.dataset.criterion,
      input.valueAsNumber,
    ]),
  );
}

function updateWeightNormalization(analysis) {
  for (const weight of analysis.changed.weights) {
    const output = weightFields.querySelector(`[data-normalized="${weight.criterion_id}"]`);
    if (output) output.textContent = formatShare(weight.normalized);
  }
}

function setupWeightEditor() {
  if (!currentReport || !analysisDocuments.matrix || !analysisDocuments.base_weights) {
    weightEditor.hidden = true;
    return;
  }
  const analysis = currentReport.analyses.weight_sensitivity;
  const changed = new Map(analysis.changed.weights.map((weight) => [weight.criterion_id, weight]));
  weightFields.replaceChildren(
    ...currentReport.matrix.criteria.map((criterion) => {
      const weight = changed.get(criterion.criterion_id);
      return el(
        "div",
        { class: "weight-control" },
        el("label", { for: `weight-${criterion.criterion_id}` }, criterion.name),
        el("input", {
          id: `weight-${criterion.criterion_id}`,
          type: "number",
          min: "0",
          step: "any",
          value: String(weight.input),
          "data-criterion": criterion.criterion_id,
        }),
        el("span", { class: "normalized-weight" }, "Normalizado: ", el("strong", { "data-normalized": criterion.criterion_id }, formatShare(weight.normalized))),
      );
    }),
  );
  lastAcceptedWeights = weightsFromAnalysis(analysis.changed);
  document.querySelector("#export-weights").disabled = false;
  weightError.hidden = true;
  weightStatus.textContent = "";
  weightEditor.hidden = false;
}

async function recalculateWeights() {
  const changedWeights = readWeightControls();
  if (Object.values(changedWeights).some((value) => !Number.isFinite(value))) {
    weightError.textContent = "Todos os pesos devem ser números.";
    weightError.hidden = false;
    return;
  }
  const requestId = ++latestSensitivity;
  if (sensitivityController) sensitivityController.abort();
  sensitivityController = new AbortController();
  weightError.hidden = true;
  weightStatus.textContent = "Recalculando…";
  downloadReport.hidden = true;
  document.querySelector("#export-weights").disabled = true;
  document.querySelector("#sensibilidade")?.classList.add("stale-result");
  try {
    const response = await fetch("api/weight-sensitivity", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(buildSensitivityPayload(analysisDocuments, changedWeights)),
      signal: sensitivityController.signal,
    });
    const data = await response.json();
    if (requestId !== latestSensitivity) return;
    if (!response.ok) throw new Error(data.error?.message ?? "Pesos inválidos.");
    const sensitivity = validateSensitivityResponse(data);
    currentReport.analyses.weight_sensitivity = sensitivity.analysis;
    currentReport.inputs.changed_weights = "pesos-ajustados.json";
    lastAcceptedWeights = changedWeights;
    const criteria = new Map(
      currentReport.matrix.criteria.map((criterion) => [criterion.criterion_id, criterion]),
    );
    document.querySelector("#sensibilidade")?.replaceWith(
      sensitivitySection(sensitivity.analysis, criteria).node,
    );
    reportName.textContent = `${currentReport.matrix.name} (gerado no navegador; pesos ajustados)`;
    updateDownload(currentReport);
    updateWeightNormalization(sensitivity.analysis);
    document.querySelector("#export-weights").disabled = false;
    weightStatus.textContent = "Ranking atualizado.";
  } catch (error) {
    if (error.name === "AbortError" || requestId !== latestSensitivity) return;
    weightError.textContent = error.message;
    weightError.hidden = false;
    weightStatus.textContent = "O relatório exibido corresponde ao último ajuste válido.";
  }
}

weightForm.addEventListener("submit", (event) => {
  event.preventDefault();
  recalculateWeights();
});
weightFields.addEventListener("input", () => {
  window.clearTimeout(sensitivityTimer);
  sensitivityTimer = window.setTimeout(recalculateWeights, 300);
});
document.querySelector("#restore-weights").addEventListener("click", () => {
  if (!currentReport) return;
  const base = weightsFromAnalysis(currentReport.analyses.weight_sensitivity.base);
  for (const input of weightFields.querySelectorAll("input[data-criterion]")) {
    input.value = base[input.dataset.criterion];
  }
  recalculateWeights();
});
document.querySelector("#export-weights").addEventListener("click", () => {
  if (!lastAcceptedWeights) return;
  const blob = new Blob([`${JSON.stringify(lastAcceptedWeights, null, 2)}\n`], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = el("a", { href: url, download: "pesos-ajustados.json" });
  link.click();
  URL.revokeObjectURL(url);
});

if (window.__RANKLAB_STANDALONE__) {
  const embeddedReport = document.querySelector("#ranklab-report");
  try {
    presentReport(
      JSON.parse(embeddedReport.textContent),
      "arquivo standalone",
      "Gere o relatório novamente para corrigir o arquivo.",
    );
  } catch (error) {
    showError(
      "Não foi possível exibir o relatório",
      `O relatório embutido é inválido: ${error.message}`,
      "Gere o relatório novamente.",
    );
  }
} else {
  loadFromServer();
}
