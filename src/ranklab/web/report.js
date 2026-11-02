// Regras do visualizador sem acesso ao DOM. Nenhuma função aqui recalcula uma
// análise: os números vêm do relatório e são apenas validados e formatados.

export const SUPPORTED_VERSION = 2;

export class ReportFormatError extends Error {}

const REQUIRED_FIELDS = {
  ordering_divergence: [
    "question", "first", "second", "positions", "discordant_pair_count",
    "possible_pair_count", "kendall_normalized_distance", "pair_explanation",
  ],
  proximity: [
    "question", "item_ids", "criterion_definitions", "source_values", "distance",
    "normalization", "metric", "interpretation", "limitations",
  ],
  order_selection: ["question", "source", "order", "value", "definition"],
  weight_sensitivity: ["question", "base", "changed", "items", "ranking_divergence"],
};

function isObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Rejeita o que não é um relatório suportado, em vez de renderizar seções vazias. */
export function validateReport(report) {
  if (!isObject(report) || report.format !== "ranklab-audit-report") {
    throw new ReportFormatError(
      "O arquivo não é um relatório do RankLab. Gere um com o comando audit-report.",
    );
  }
  if (report.format_version !== SUPPORTED_VERSION) {
    throw new ReportFormatError(
      `O relatório usa o formato ${report.format_version}, e este visualizador lê o formato ` +
        `${SUPPORTED_VERSION}. Gere o relatório novamente com o comando audit-report.`,
    );
  }
  if (!isObject(report.analyses) || !isObject(report.inputs) || !isObject(report.matrix)) {
    throw new ReportFormatError("O relatório precisa conter inputs, matrix e analyses.");
  }
  for (const [section, fields] of Object.entries(REQUIRED_FIELDS)) {
    const analysis = report.analyses[section];
    if (!isObject(analysis)) {
      throw new ReportFormatError(`O relatório está sem a análise ${section}.`);
    }
    const missing = fields.filter((field) => !(field in analysis));
    if (missing.length > 0) {
      throw new ReportFormatError(
        `A análise ${section} está incompleta. Campos ausentes: ${missing.join(", ")}.`,
      );
    }
  }
  return report;
}

export function formatNumber(value, maximumFractionDigits = 6) {
  if (typeof value !== "number") return String(value);
  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits,
    useGrouping: false,
  }).format(value);
}

export function formatSignedNumber(value, maximumFractionDigits = 6) {
  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits,
    useGrouping: false,
    signDisplay: "exceptZero",
  }).format(value);
}

export function formatShare(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}

/** Variação positiva significa subida: a posição numérica diminuiu. */
export function describeDelta(delta) {
  if (delta > 0) return { mark: "▲", text: `${formatSignedNumber(delta, 0)} subiu`, tone: "up" };
  if (delta < 0) return { mark: "▼", text: `${formatSignedNumber(delta, 0)} caiu`, tone: "down" };
  return { mark: "=", text: "inalterado", tone: "same" };
}

export function directionLabel(direction) {
  if (direction === "higher_is_better") return "maior é melhor";
  if (direction === "lower_is_better") return "menor é melhor";
  return String(direction);
}

export function orderingAnswer({ discordant_pair_count: count, possible_pair_count: total }) {
  if (total === 0) return "Os rankings têm menos de dois itens, então não há pares para comparar.";
  if (count === 0) return "Nenhum par inverteu de ordem.";
  return `${count} de ${total} pares ${count === 1 ? "inverteu" : "inverteram"} de ordem.`;
}

export function proximityAnswer({ item_ids: [first, second], criterion_definitions: criteria, distance }) {
  const names = criteria.map((criterion) => criterion.name).join(" e ");
  return `${first} e ${second} são o par mais próximo em ${names}, a uma distância de ${formatNumber(distance)}.`;
}

function selectionValue({ value, source }) {
  const formatted = formatNumber(value);
  return source.unit ? `${formatted} ${source.unit}` : formatted;
}

export function selectionAnswer(selection) {
  const { percentile, order, source } = selection;
  const collection = source.name ? ` de ${source.name}` : " da coleção";
  const value = selectionValue(selection);
  if (percentile === null || percentile === undefined) {
    return `O elemento de ordem k = ${order}${collection} é ${value}.`;
  }
  return `O percentil ${formatNumber(percentile)}${collection} é ${value}, na ordem k = ${order}.`;
}

export function sensitivityAnswer({ items }) {
  const moved = items.filter((item) => item.position_delta !== 0).length;
  if (moved === 0) return "Nenhum item mudou de posição com os pesos alterados.";
  const verb = moved === 1 ? "mudou" : "mudaram";
  return `${moved} de ${items.length} itens ${verb} de posição com os pesos alterados.`;
}
