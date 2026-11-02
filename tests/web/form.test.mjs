import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  buildReportPayload,
  buildSensitivityPayload,
  criteriaFromMatrix,
  validateSensitivityResponse,
  weightsFromAnalysis,
} from "../../src/ranklab/web/form.js";

const documents = {
  matrix: { source: "matriz.json", content: "{}" },
  first_ranking: { source: "first.json", content: "{}" },
  second_ranking: { source: "second.json", content: "{}" },
  base_weights: { source: "base.json", content: "{}" },
  changed_weights: { source: "changed.json", content: "{}" },
  selection_values: { source: "values.json", content: "[]" },
};

test("criteriaFromMatrix extrai IDs e nomes sem calcular a análise", () => {
  const criteria = criteriaFromMatrix(JSON.stringify({
    criteria: [
      { criterion_id: "qualidade", name: "Qualidade", unit: "pontos" },
      { criterion_id: "prazo", name: "Prazo", unit: "dias" },
    ],
  }));

  assert.deepEqual(criteria.map(({ criterion_id }) => criterion_id), ["qualidade", "prazo"]);
});

test("buildReportPayload representa critério, percentil e rastreamento", () => {
  const payload = buildReportPayload(documents, {
    closestCriteria: ["qualidade", "prazo"],
    selectionSource: "matrix_criterion",
    selectionCriterion: "qualidade",
    orderType: "percentile",
    orderValue: 50,
    includeTraces: true,
  });

  assert.deepEqual(payload.parameters.selection, {
    source: { type: "matrix_criterion", criterion_id: "qualidade" },
    percentile: 50,
  });
  assert.equal(payload.parameters.include_traces, true);
  assert.equal("selection_values" in payload.inputs, false);
});

test("buildReportPayload inclui lista externa e ordem k", () => {
  const payload = buildReportPayload(documents, {
    closestCriteria: ["qualidade", "prazo"],
    selectionSource: "json_list",
    selectionCriterion: "",
    orderType: "k",
    orderValue: 3,
    includeTraces: false,
  });

  assert.equal(payload.inputs.selection_values.source, "values.json");
  assert.deepEqual(payload.parameters.selection, { source: { type: "json_list" }, k: 3 });
});

test("payload de sensibilidade serializa somente os pesos ajustados", () => {
  const payload = buildSensitivityPayload(documents, { qualidade: 1, prazo: 3 });

  assert.deepEqual(JSON.parse(payload.inputs.changed_weights.content), { qualidade: 1, prazo: 3 });
  assert.equal(payload.inputs.changed_weights.source, "pesos-ajustados.json");
});

test("resposta de sensibilidade é validada e pesos de entrada são recuperados", () => {
  const response = {
    format: "ranklab-weight-sensitivity",
    format_version: 1,
    matrix: {},
    analysis: {},
  };
  assert.equal(validateSensitivityResponse(response), response);
  assert.deepEqual(
    weightsFromAnalysis({ weights: [{ criterion_id: "a", input: 2 }, { criterion_id: "b", input: 1 }] }),
    { a: 2, b: 1 },
  );
  assert.throws(() => validateSensitivityResponse({}), /formato inválido/);
});

test("formulário usa controles nativos rotulados e não altera a ordem de foco", () => {
  const html = readFileSync("src/ranklab/web/index.html", "utf8");

  for (const id of [
    "matrix-file",
    "first-ranking-file",
    "second-ranking-file",
    "base-weights-file",
    "changed-weights-file",
    "closest-first",
    "closest-second",
    "selection-criterion",
  ]) {
    assert.match(html, new RegExp(`<label for="${id}">`));
  }
  assert.doesNotMatch(html, /tabindex="[1-9]/);
  assert.match(html, /<button id="generate-report" type="submit">/);
});
