// Transformações puras do formulário. A validação dos dados e os cálculos
// permanecem no Python; estas funções apenas montam o contrato HTTP.

export function criteriaFromMatrix(content) {
  const matrix = JSON.parse(content);
  if (!matrix || typeof matrix !== "object" || !Array.isArray(matrix.criteria)) {
    throw new Error("A matriz precisa conter uma lista criteria.");
  }
  const criteria = matrix.criteria.map((criterion) => {
    if (!criterion || typeof criterion.criterion_id !== "string" || !criterion.criterion_id) {
      throw new Error("Cada critério precisa de um criterion_id.");
    }
    return {
      criterion_id: criterion.criterion_id,
      name: typeof criterion.name === "string" ? criterion.name : criterion.criterion_id,
      unit: typeof criterion.unit === "string" ? criterion.unit : "",
    };
  });
  if (criteria.length < 2) throw new Error("A matriz precisa ter ao menos dois critérios para proximidade.");
  return criteria;
}

export function buildReportPayload(documents, parameters) {
  const inputs = {
    matrix: documents.matrix,
    first_ranking: documents.first_ranking,
    second_ranking: documents.second_ranking,
    base_weights: documents.base_weights,
    changed_weights: documents.changed_weights,
  };
  const selection = {
    source:
      parameters.selectionSource === "matrix_criterion"
        ? { type: "matrix_criterion", criterion_id: parameters.selectionCriterion }
        : { type: "json_list" },
  };
  if (parameters.selectionSource === "json_list") {
    inputs.selection_values = documents.selection_values;
  }
  if (parameters.orderType === "k") selection.k = parameters.orderValue;
  else selection.percentile = parameters.orderValue;
  return {
    inputs,
    parameters: {
      closest_criteria: parameters.closestCriteria,
      selection,
      include_traces: parameters.includeTraces,
    },
  };
}

export function buildSensitivityPayload(documents, changedWeights) {
  return {
    inputs: {
      matrix: documents.matrix,
      base_weights: documents.base_weights,
      changed_weights: {
        source: "pesos-ajustados.json",
        content: JSON.stringify(changedWeights),
      },
    },
  };
}

export function validateSensitivityResponse(data) {
  if (
    !data ||
    data.format !== "ranklab-weight-sensitivity" ||
    data.format_version !== 1 ||
    !data.matrix ||
    !data.analysis
  ) {
    throw new Error("A API retornou uma comparação de pesos em formato inválido.");
  }
  return data;
}

export function weightsFromAnalysis(scenario) {
  return Object.fromEntries(scenario.weights.map((weight) => [weight.criterion_id, weight.input]));
}
