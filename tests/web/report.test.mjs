import assert from "node:assert/strict";
import { test } from "node:test";

import {
  ReportFormatError,
  describeDelta,
  formatNumber,
  formatSignedNumber,
  orderingAnswer,
  selectionAnswer,
  sensitivityAnswer,
  validateReport,
} from "../../src/ranklab/web/report.js";

function validReport() {
  return {
    format: "ranklab-audit-report",
    format_version: 2,
    inputs: {},
    matrix: {},
    analyses: {
      ordering_divergence: {
        question: "", first: {}, second: {}, positions: [], discordant_pair_count: 0,
        possible_pair_count: 0, kendall_normalized_distance: 0, pair_explanation: "",
      },
      proximity: {
        question: "", item_ids: [], criterion_definitions: [], source_values: {}, distance: 0,
        normalization: "", metric: "", interpretation: "", limitations: [],
      },
      order_selection: { question: "", source: {}, order: 1, value: 1, definition: "" },
      weight_sensitivity: { question: "", base: {}, changed: {}, items: [], ranking_divergence: {} },
    },
  };
}

test("validateReport aceita um relatório completo", () => {
  const report = validReport();

  assert.equal(validateReport(report), report);
});

test("validateReport rejeita outro formato", () => {
  assert.throws(() => validateReport({ format: "outro" }), ReportFormatError);
  assert.throws(() => validateReport([]), ReportFormatError);
  assert.throws(() => validateReport(null), ReportFormatError);
});

test("validateReport informa a versão incompatível", () => {
  assert.throws(
    () => validateReport({ ...validReport(), format_version: 1 }),
    /usa o formato 1/,
  );
});

test("validateReport nomeia a análise ausente", () => {
  const report = validReport();
  delete report.analyses.proximity;

  assert.throws(() => validateReport(report), /sem a análise proximity/);
});

test("validateReport nomeia o campo ausente", () => {
  const report = validReport();
  delete report.analyses.weight_sensitivity.items;

  assert.throws(() => validateReport(report), /weight_sensitivity.*items/);
});

test("formatNumber usa vírgula decimal e limita casas só na exibição", () => {
  assert.equal(formatNumber(1 / 3), "0,333333");
  assert.equal(formatNumber(90), "90");
});

test("formatNumber preserva valor não numérico de uma lista de seleção", () => {
  assert.equal(formatNumber("beta"), "beta");
});

test("formatSignedNumber marca o sinal e deixa o zero sem sinal", () => {
  assert.equal(formatSignedNumber(0.5), "+0,5");
  assert.equal(formatSignedNumber(0), "0");
});

test("describeDelta trata variação positiva como subida", () => {
  assert.deepEqual(describeDelta(1), { mark: "▲", text: "+1 subiu", tone: "up" });
  assert.deepEqual(describeDelta(-2), { mark: "▼", text: "-2 caiu", tone: "down" });
  assert.deepEqual(describeDelta(0), { mark: "=", text: "inalterado", tone: "same" });
});

test("orderingAnswer concorda com a contagem", () => {
  const answer = (count, total) =>
    orderingAnswer({ discordant_pair_count: count, possible_pair_count: total });

  assert.equal(answer(1, 3), "1 de 3 pares inverteu de ordem.");
  assert.equal(answer(2, 3), "2 de 3 pares inverteram de ordem.");
  assert.equal(answer(0, 3), "Nenhum par inverteu de ordem.");
  assert.match(answer(0, 0), /não há pares/);
});

test("selectionAnswer diferencia percentil de ordem direta", () => {
  const source = { name: "Qualidade técnica", unit: "pontos" };

  assert.equal(
    selectionAnswer({ percentile: 50, order: 2, value: 90, source }),
    "O percentil 50 de Qualidade técnica é 90 pontos, na ordem k = 2.",
  );
  assert.equal(
    selectionAnswer({ percentile: null, order: 1, value: 7, source: {} }),
    "O elemento de ordem k = 1 da coleção é 7.",
  );
});

test("sensitivityAnswer conta apenas itens que mudaram de posição", () => {
  const items = [{ position_delta: 1 }, { position_delta: -1 }, { position_delta: 0 }];

  assert.equal(
    sensitivityAnswer({ items }),
    "2 de 3 itens mudaram de posição com os pesos alterados.",
  );
  assert.equal(
    sensitivityAnswer({ items: [{ position_delta: 0 }] }),
    "Nenhum item mudou de posição com os pesos alterados.",
  );
});
