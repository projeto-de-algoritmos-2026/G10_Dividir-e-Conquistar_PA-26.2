// Geometria dos gráficos, sem acesso ao DOM. Os valores vêm do relatório; aqui
// só se decide onde desenhá-los.

export const SLOPE_ITEM_LIMIT = 40;

function compareIds(first, second) {
  return first < second ? -1 : first > second ? 1 : 0;
}

/**
 * Posiciona as linhas pela ordem de cada lado, não pela posição absoluta.
 *
 * Acima do limite, mantém os itens com maior variação. Reindexar preserva a
 * ordem relativa, então duas linhas exibidas se cruzam se e somente se o par é
 * discordante também nos rankings completos.
 */
export function slopeModel(rows, limit = SLOPE_ITEM_LIMIT) {
  const shown =
    rows.length <= limit
      ? rows
      : [...rows]
          .sort(
            (first, second) =>
              Math.abs(second.delta) - Math.abs(first.delta) || compareIds(first.itemId, second.itemId),
          )
          .slice(0, limit);

  const indexBy = (position) =>
    new Map(
      [...shown]
        .sort((first, second) => first[position] - second[position])
        .map((row, index) => [row.itemId, index]),
    );
  const leftIndex = indexBy("left");
  const rightIndex = indexBy("right");

  return {
    total: rows.length,
    truncated: shown.length < rows.length,
    hasChanges: rows.some((row) => row.delta !== 0),
    lines: shown.map((row) => ({
      ...row,
      leftIndex: leftIndex.get(row.itemId),
      rightIndex: rightIndex.get(row.itemId),
    })),
  };
}

export function linesCross(first, second) {
  return (first.leftIndex - second.leftIndex) * (first.rightIndex - second.rightIndex) < 0;
}

/** Junta pontos idênticos, para que nenhum item fique escondido sob outro. */
function groupCoincidentPoints(points, pairIds, [xId, yId]) {
  const groups = new Map();
  for (const point of points) {
    const x = point.normalized_values[xId];
    const y = point.normalized_values[yId];
    const key = `${x}|${y}`;
    if (!groups.has(key)) groups.set(key, { key, x, y, points: [], isPair: false });
    const group = groups.get(key);
    group.points.push(point);
    group.isPair ||= pairIds.includes(point.item_id);
  }
  return [...groups.values()];
}

function axisModel(points, criterion) {
  const id = criterion.criterion_id;
  const sourceAt = (normalized) =>
    points.find((point) => point.normalized_values[id] === normalized)?.source_values[id] ?? null;
  const sources = points.map((point) => point.source_values[id]);
  return {
    criterion,
    constant: Math.min(...sources) === Math.max(...sources),
    low: sourceAt(0),
    high: sourceAt(1),
  };
}

const EDGE_MARGIN = 0.12;

function besideSide(group) {
  return group.x > 0.5 ? "beside-left" : "beside-right";
}

/**
 * Coloca os rótulos em lados opostos, pois os pontos do par são próximos por
 * definição. Perto da borda não há espaço acima ou abaixo: o rótulo vai para o
 * lado. Só um dos dois fica ao lado quando os pontos estão próximos, o que evita
 * sobreposição entre os rótulos.
 */
function pairLabels(first, second) {
  const firstOnTop = first.y > second.y || (first.y === second.y && first.x <= second.x);
  const [upper, lower] = firstOnTop ? [first, second] : [second, first];
  return new Map([
    [upper.key, upper.y > 1 - EDGE_MARGIN ? besideSide(upper) : "above"],
    [lower.key, lower.y < EDGE_MARGIN ? besideSide(lower) : "below"],
  ]);
}

/** Rótulo temporário de um ponto que não pertence ao par. */
export function activeLabelSide(y) {
  return y > 1 - EDGE_MARGIN ? "below" : "above";
}

export function labelAlignment(x) {
  if (x < 0.2) return "start";
  if (x > 0.8) return "end";
  return "center";
}

export function scatterModel(proximity) {
  const { points, item_ids: pairIds, criterion_definitions: criteria } = proximity;
  const ids = criteria.map((criterion) => criterion.criterion_id);
  const groups = groupCoincidentPoints(points, pairIds, ids);
  const pairGroups = pairIds.map((itemId) =>
    groups.find((group) => group.points.some((point) => point.item_id === itemId)),
  );
  const [first, second] = pairGroups;
  const coincident = first === second;

  return {
    groups,
    axes: criteria.map((criterion) => axisModel(points, criterion)),
    segment: coincident ? null : { x1: first.x, y1: first.y, x2: second.x, y2: second.y },
    labels: coincident ? new Map([[first.key, "above"]]) : pairLabels(first, second),
  };
}
