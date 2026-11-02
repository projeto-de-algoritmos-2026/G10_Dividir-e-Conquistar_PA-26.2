import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { activeLabelSide, labelAlignment, linesCross, scatterModel, slopeModel } from "../../src/ranklab/web/charts.js";
import { validateReport } from "../../src/ranklab/web/report.js";

const demoReport = JSON.parse(readFileSync(new URL("./relatorio-demo.json", import.meta.url), "utf-8"));

function rowsFromOrders(first, second) {
  return first.map((itemId, index) => {
    const right = second.indexOf(itemId) + 1;
    return { itemId, left: index + 1, right, delta: index + 1 - right };
  });
}

function pairKey(first, second) {
  return [first, second].sort().join("|");
}

function crossingPairs(lines) {
  const pairs = new Set();
  lines.forEach((first, index) => {
    for (const second of lines.slice(index + 1)) {
      if (linesCross(first, second)) pairs.add(pairKey(first.itemId, second.itemId));
    }
  });
  return pairs;
}

// Oráculo quadrático: compara diretamente a ordem relativa nos dois lados.
function discordantPairs(rows) {
  const pairs = new Set();
  rows.forEach((first, index) => {
    for (const second of rows.slice(index + 1)) {
      if ((first.left - second.left) * (first.right - second.right) < 0) {
        pairs.add(pairKey(first.itemId, second.itemId));
      }
    }
  });
  return pairs;
}

function seededShuffle(values, seed) {
  const shuffled = [...values];
  let state = seed;
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    state = (state * 1103515245 + 12345) % 2147483648;
    const other = state % (index + 1);
    [shuffled[index], shuffled[other]] = [shuffled[other], shuffled[index]];
  }
  return shuffled;
}

function ids(count) {
  return Array.from({ length: count }, (_, index) => `item-${String(index).padStart(3, "0")}`);
}

test("o relatório gerado pelo Python passa na validação do cliente", () => {
  assert.equal(validateReport(demoReport), demoReport);
});

test("cruzamentos do gráfico são os pares discordantes do relatório", () => {
  const analysis = demoReport.analyses.ordering_divergence;
  const model = slopeModel(
    analysis.positions.map((item) => ({
      itemId: item.item_id,
      left: item.first_position,
      right: item.second_position,
      delta: item.position_delta,
    })),
  );

  assert.deepEqual(
    crossingPairs(model.lines),
    new Set(analysis.discordant_pairs.map((pair) => pairKey(pair.earlier_in_first, pair.later_in_first))),
  );
});

test("cruzamentos do gráfico são os cruzamentos relatados na sensibilidade", () => {
  const { items } = demoReport.analyses.weight_sensitivity;
  const model = slopeModel(
    items.map((item) => ({
      itemId: item.item_id,
      left: item.base_position,
      right: item.changed_position,
      delta: item.position_delta,
    })),
  );

  const reported = new Set(
    items.flatMap((item) => item.crossed_item_ids.map((other) => pairKey(item.item_id, other))),
  );
  assert.deepEqual(crossingPairs(model.lines), reported);
});

test("cruzamentos conferem com o oráculo em permutações", () => {
  for (const seed of [1, 7, 42, 1000]) {
    const items = ids(25);
    const rows = rowsFromOrders(items, seededShuffle(items, seed));

    assert.deepEqual(crossingPairs(slopeModel(rows).lines), discordantPairs(rows));
  }
});

test("corte por limite mantém os itens de maior variação e informa o total", () => {
  const items = ids(60);
  const rows = rowsFromOrders(items, seededShuffle(items, 5));

  const model = slopeModel(rows, 40);
  const smallestShown = Math.min(...model.lines.map((line) => Math.abs(line.delta)));
  const shownIds = new Set(model.lines.map((line) => line.itemId));
  const largestHidden = Math.max(
    ...rows.filter((row) => !shownIds.has(row.itemId)).map((row) => Math.abs(row.delta)),
  );

  assert.equal(model.lines.length, 40);
  assert.equal(model.total, 60);
  assert.equal(model.truncated, true);
  assert.ok(smallestShown >= largestHidden);
});

test("corte por limite preserva os cruzamentos entre os itens exibidos", () => {
  const items = ids(60);
  const rows = rowsFromOrders(items, seededShuffle(items, 9));

  const model = slopeModel(rows, 40);
  const shownIds = new Set(model.lines.map((line) => line.itemId));
  const shownRows = rows.filter((row) => shownIds.has(row.itemId));

  assert.deepEqual(crossingPairs(model.lines), discordantPairs(shownRows));
  assert.deepEqual(
    model.lines.map((line) => line.leftIndex).sort((first, second) => first - second),
    Array.from({ length: 40 }, (_, index) => index),
  );
});

test("corte por limite é determinístico em empates de variação", () => {
  const items = ids(50);
  const rows = rowsFromOrders(items, items);

  assert.deepEqual(
    slopeModel(rows, 3).lines.map((line) => line.itemId),
    ["item-000", "item-001", "item-002"],
  );
});

test("modelo sem mudanças não tem cruzamentos", () => {
  const items = ids(5);
  const model = slopeModel(rowsFromOrders(items, items));

  assert.equal(model.hasChanges, false);
  assert.equal(crossingPairs(model.lines).size, 0);
});

function proximityFrom(rows, itemIds) {
  return {
    item_ids: itemIds,
    criterion_definitions: [
      { criterion_id: "x", name: "X", direction: "higher_is_better", unit: "u" },
      { criterion_id: "y", name: "Y", direction: "lower_is_better", unit: "u" },
    ],
    points: rows.map(([itemId, x, y, sourceX = x, sourceY = y]) => ({
      item_id: itemId,
      normalized_values: { x, y },
      source_values: { x: sourceX, y: sourceY },
    })),
  };
}

test("segmento desenhado mede a distância informada no relatório", () => {
  const proximity = demoReport.analyses.proximity;

  const { segment } = scatterModel(proximity);

  const drawn = Math.hypot(segment.x2 - segment.x1, segment.y2 - segment.y1);
  assert.ok(Math.abs(drawn - proximity.distance) < 1e-12);
});

test("todos os itens do relatório aparecem nos pontos", () => {
  const proximity = demoReport.analyses.proximity;

  const { groups } = scatterModel(proximity);

  assert.deepEqual(
    groups.flatMap((group) => group.points.map((point) => point.item_id)).sort(),
    proximity.points.map((point) => point.item_id).sort(),
  );
});

test("eixo de critério invertido mostra o melhor valor de origem na extremidade 1", () => {
  const { axes } = scatterModel(demoReport.analyses.proximity);
  const deadline = axes.find((axis) => axis.criterion.criterion_id === "prazo_dias");

  assert.equal(deadline.low, 15);
  assert.equal(deadline.high, 9);
  assert.equal(deadline.constant, false);
});

test("pontos coincidentes formam um grupo que identifica todos os itens", () => {
  const model = scatterModel(proximityFrom([["a", 0.5, 0.5], ["b", 0.5, 0.5], ["c", 1, 0]], ["a", "b"]));

  const [group] = model.groups.filter((candidate) => candidate.points.length === 2);

  assert.deepEqual(group.points.map((point) => point.item_id), ["a", "b"]);
  assert.equal(group.isPair, true);
  assert.equal(model.segment, null);
  assert.equal(model.labels.size, 1);
});

test("coluna constante é identificada e não tem extremidade 1", () => {
  const model = scatterModel(proximityFrom([["a", 0, 0, 5, 1], ["b", 0, 1, 5, 3]], ["a", "b"]));

  assert.equal(model.axes[0].constant, true);
  assert.equal(model.axes[0].low, 5);
  assert.equal(model.axes[0].high, null);
  assert.equal(model.axes[1].constant, false);
});

test("rótulos do par ficam em lados opostos, mesmo com y igual", () => {
  const sides = (rows) => [...scatterModel(proximityFrom(rows, ["a", "b"])).labels.values()].sort();

  assert.deepEqual(sides([["a", 0.5, 0.7], ["b", 0.5, 0.3]]), ["above", "below"]);
  assert.deepEqual(sides([["a", 0.2, 0.5], ["b", 0.8, 0.5]]), ["above", "below"]);
});

test("rótulo do par vai para o lado quando não há espaço acima ou abaixo", () => {
  const labelOf = (rows, itemId) => {
    const model = scatterModel(proximityFrom(rows, ["a", "b"]));
    const group = model.groups.find((candidate) => candidate.points[0].item_id === itemId);
    return model.labels.get(group.key);
  };
  const bottom = [["a", 0.3, 0], ["b", 0.9, 0.5]];
  const top = [["a", 0.9, 1], ["b", 0.3, 0.5]];

  assert.equal(labelOf(bottom, "a"), "beside-right");
  assert.equal(labelOf(bottom, "b"), "above");
  assert.equal(labelOf(top, "a"), "beside-left");
  assert.equal(labelOf(top, "b"), "below");
});

test("par próximo junto à borda mantém um rótulo fora do lado", () => {
  const model = scatterModel(proximityFrom([["a", 0.5, 0.02], ["b", 0.51, 0.02]], ["a", "b"]));

  assert.deepEqual([...model.labels.values()].sort(), ["above", "beside-left"].sort());
});

test("rótulo temporário no topo do gráfico fica abaixo do ponto", () => {
  assert.equal(activeLabelSide(1), "below");
  assert.equal(activeLabelSide(0.5), "above");
});

test("rótulo perto da borda é alinhado para dentro do gráfico", () => {
  assert.equal(labelAlignment(0), "start");
  assert.equal(labelAlignment(0.5), "center");
  assert.equal(labelAlignment(1), "end");
});
