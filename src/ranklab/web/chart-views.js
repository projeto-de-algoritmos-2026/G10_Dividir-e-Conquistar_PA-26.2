import { SLOPE_ITEM_LIMIT, activeLabelSide, labelAlignment, scatterModel, slopeModel } from "./charts.js";
import { el, svg } from "./dom.js";
import { describeDelta, formatNumber } from "./report.js";

// Um único ponto de parada no Tab por gráfico; as setas percorrem os itens.
function bindArrowNavigation(container, targets) {
  targets.forEach((target, index) => target.setAttribute("tabindex", index === 0 ? "0" : "-1"));
  container.addEventListener("keydown", (event) => {
    const current = targets.indexOf(document.activeElement);
    if (current === -1) return;
    const last = targets.length - 1;
    const next = {
      ArrowDown: Math.min(current + 1, last),
      ArrowRight: Math.min(current + 1, last),
      ArrowUp: Math.max(current - 1, 0),
      ArrowLeft: Math.max(current - 1, 0),
      Home: 0,
      End: last,
    }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    targets[current].setAttribute("tabindex", "-1");
    targets[next].setAttribute("tabindex", "0");
    targets[next].focus();
  });
}

// Mouse e foco destacam enquanto duram; clique ou toque fixa, Esc limpa.
function bindHighlight(container, onChange) {
  let hovered = null;
  let focused = null;
  let pinned = null;
  const update = () => onChange(hovered ?? focused ?? pinned, pinned);
  const keyOf = (target) => target.closest?.("[data-key]")?.dataset.key ?? null;

  container.addEventListener("pointerover", (event) => {
    hovered = keyOf(event.target);
    update();
  });
  container.addEventListener("pointerleave", () => {
    hovered = null;
    update();
  });
  container.addEventListener("focusin", (event) => {
    focused = keyOf(event.target);
    update();
  });
  container.addEventListener("focusout", () => {
    focused = null;
    update();
  });
  container.addEventListener("click", (event) => {
    const key = keyOf(event.target);
    if (key === null) return;
    pinned = pinned === key ? null : key;
    update();
  });
  container.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    hovered = null;
    focused = null;
    pinned = null;
    update();
  });
}

function slopeDescription(line, partners, { leftLabel, rightLabel }) {
  const movement = `Posição ${line.left} em ${leftLabel} e ${line.right} em ${rightLabel}; ${describeDelta(line.delta).text}.`;
  let pairs;
  if (partners === null) pairs = "Pares omitidos pelo limite de itens do relatório.";
  else if (partners.length === 0) pairs = "Nenhum par discordante.";
  else pairs = `Par discordante com ${partners.join(", ")}.`;
  return `${line.itemId}: ${movement} ${pairs}`;
}

/**
 * Gráfico de inclinação. Os rótulos são HTML, com tamanho de fonte estável; o
 * SVG central estica na largura disponível sem deformar a espessura das linhas.
 */
export function slopeChart({ rows, partnersOf, leftLabel, rightLabel, unchangedText }) {
  const model = slopeModel(rows);
  const rowCount = model.lines.length;
  const partners = new Map(model.lines.map((line) => [line.itemId, partnersOf(line.itemId)]));
  const descriptions = new Map(
    model.lines.map((line) => [
      line.itemId,
      slopeDescription(line, partners.get(line.itemId), { leftLabel, rightLabel }),
    ]),
  );
  const byIndex = (side) =>
    [...model.lines].sort((first, second) => first[side] - second[side]);

  const leftButtons = byIndex("leftIndex").map((line) =>
    el(
      "button",
      {
        type: "button",
        class: "slope-label slope-label-left",
        "data-key": line.itemId,
        "aria-label": descriptions.get(line.itemId),
        "aria-pressed": "false",
      },
      el("span", { class: "slope-name" }, line.itemId),
      el("span", { class: "slope-position" }, String(line.left)),
    ),
  );
  const rightLabels = byIndex("rightIndex").map((line) => {
    const { mark, tone } = describeDelta(line.delta);
    return el(
      "div",
      { class: "slope-label slope-label-right", "data-key": line.itemId },
      el("span", { class: "slope-position" }, String(line.right)),
      el("span", { class: "slope-name" }, line.itemId),
      el("span", { class: `slope-mark ${tone}` }, mark),
    );
  });
  const lineGroups = model.lines.map((line) => {
    const y1 = String(line.leftIndex + 0.5);
    const y2 = String(line.rightIndex + 0.5);
    const coordinates = { x1: "0", x2: "100", y1, y2, "vector-effect": "non-scaling-stroke" };
    return svg(
      "g",
      { class: `slope-line ${describeDelta(line.delta).tone}`, "data-key": line.itemId },
      svg("line", { ...coordinates, class: "slope-hit" }),
      svg("line", { ...coordinates, class: "slope-stroke" }),
    );
  });
  const plot = svg(
    "svg",
    {
      class: "slope-plot",
      viewBox: `0 0 100 ${rowCount}`,
      preserveAspectRatio: "none",
      "aria-hidden": "true",
      focusable: "false",
    },
    ...lineGroups,
  );
  plot.style.setProperty("--rows", String(rowCount));

  const hint = "Passe o mouse ou toque em um item para ver seus pares. Pelo teclado, use as setas.";
  const readout = el("p", { class: "chart-readout" }, hint);
  const grid = el(
    "div",
    { class: "slope-grid" },
    el("div", { class: "slope-heading slope-heading-left" }, leftLabel),
    el("div", { class: "slope-heading-gap" }),
    el("div", { class: "slope-heading" }, rightLabel),
    el("div", { class: "slope-column" }, ...leftButtons),
    plot,
    el("div", { class: "slope-column" }, ...rightLabels),
  );

  const chart = el(
    "figure",
    { class: "chart" },
    grid,
    readout,
    el(
      "figcaption",
      { class: "note" },
      model.hasChanges
        ? "Cada cruzamento de linhas é um par discordante. Linha contínua sobe, tracejada cai e fina não muda."
        : unchangedText,
      model.truncated
        ? ` O gráfico mostra os ${SLOPE_ITEM_LIMIT} itens com maior variação entre ${model.total}; a tabela traz todos.`
        : null,
    ),
  );

  const highlightable = [...grid.querySelectorAll("[data-key]")];
  bindHighlight(grid, (active, pinned) => {
    grid.toggleAttribute("data-active", active !== null);
    const related = new Set([active, ...(partners.get(active) ?? [])]);
    for (const node of highlightable) {
      const { key } = node.dataset;
      node.classList.toggle("is-active", key === active);
      node.classList.toggle("is-related", related.has(key));
      if (node.hasAttribute("aria-pressed")) node.setAttribute("aria-pressed", String(key === pinned));
    }
    readout.textContent = active === null ? hint : descriptions.get(active);
  });
  bindArrowNavigation(grid, leftButtons);
  return chart;
}

function axisTitle({ criterion, constant }) {
  const base = `${criterion.name} (${criterion.unit})`;
  return constant ? `${base}: coluna constante, projetada em zero` : base;
}

function tick(value, position) {
  return el("span", { class: `scatter-tick scatter-tick-${position}` }, value === null ? "" : formatNumber(value));
}

function positionAt(node, x, y) {
  node.style.setProperty("--x", `${x * 100}%`);
  node.style.setProperty("--y", `${y * 100}%`);
  return node;
}

function pointDescription(point, axes) {
  const values = axes.map(({ criterion }) => {
    const id = criterion.criterion_id;
    return `${criterion.name} ${formatNumber(point.source_values[id])} ${criterion.unit}, normalizado ${formatNumber(point.normalized_values[id])}`;
  });
  return `${point.item_id}: ${values.join("; ")}.`;
}

function groupDescription(group, axes) {
  const coincident = group.points.length > 1 ? `${group.points.length} itens no mesmo ponto. ` : "";
  const pair = group.isPair ? "Par mais próximo. " : "";
  return `${coincident}${pair}${group.points.map((point) => pointDescription(point, axes)).join(" ")}`;
}

/**
 * Dispersão quadrada, com a mesma escala nos dois eixos: uma distância
 * Euclidiana só pode ser lida no desenho se 1 em x medir o mesmo que 1 em y.
 */
export function scatterChart(proximity) {
  const model = scatterModel(proximity);
  const [xAxis, yAxis] = model.axes;
  const descriptions = new Map(model.groups.map((group) => [group.key, groupDescription(group, model.axes)]));

  const gridLines = [0, 50, 100].flatMap((at) => [
    svg("line", { x1: String(at), x2: String(at), y1: "0", y2: "100", "vector-effect": "non-scaling-stroke" }),
    svg("line", { x1: "0", x2: "100", y1: String(at), y2: String(at), "vector-effect": "non-scaling-stroke" }),
  ]);
  const segment = model.segment
    ? svg("line", {
        class: "scatter-segment",
        x1: String(model.segment.x1 * 100),
        y1: String((1 - model.segment.y1) * 100),
        x2: String(model.segment.x2 * 100),
        y2: String((1 - model.segment.y2) * 100),
        "vector-effect": "non-scaling-stroke",
      })
    : null;
  const background = svg(
    "svg",
    { class: "scatter-grid", viewBox: "0 0 100 100", preserveAspectRatio: "none", "aria-hidden": "true", focusable: "false" },
    ...gridLines,
    segment,
  );

  const markers = model.groups.map((group) => {
    const count = group.points.length;
    const classes = ["scatter-point", group.isPair ? "is-pair" : "", count > 1 ? "is-group" : ""];
    return positionAt(
      el(
        "button",
        {
          type: "button",
          class: classes.join(" ").trim(),
          "data-key": group.key,
          "aria-label": descriptions.get(group.key),
          "aria-pressed": "false",
        },
        count > 1 ? String(count) : null,
      ),
      group.x,
      group.y,
    );
  });

  const staticLabels = [...model.labels].map(([key, side]) => {
    const group = model.groups.find((candidate) => candidate.key === key);
    return positionAt(
      el(
        "span",
        { class: `scatter-label ${side} align-${labelAlignment(group.x)}` },
        group.points.map((point) => point.item_id).join(", "),
      ),
      group.x,
      group.y,
    );
  });
  const activeLabel = el("span", { class: "scatter-label above", hidden: "" });

  const plot = el("div", { class: "scatter-plot" }, background, ...staticLabels, ...markers, activeLabel);
  const hint = "Passe o mouse ou toque em um ponto para ver seus valores. Pelo teclado, use as setas.";
  const readout = el("p", { class: "chart-readout" }, hint);

  const chart = el(
    "figure",
    { class: "chart scatter" },
    el("div", { class: "scatter-title" }, axisTitle(yAxis)),
    el(
      "div",
      { class: "scatter-frame" },
      el("div", { class: "scatter-y-ticks" }, tick(yAxis.high, "high"), tick(yAxis.low, "low")),
      plot,
      el("div", { class: "scatter-x-ticks" }, tick(xAxis.low, "low"), tick(xAxis.high, "high")),
    ),
    el("div", { class: "scatter-title scatter-title-x" }, axisTitle(xAxis)),
    readout,
    el(
      "figcaption",
      { class: "note" },
      "Pontos preenchidos e ligados formam o par mais próximo. Para a direita e para cima fica o melhor valor de cada critério, na escala normalizada de 0 a 1.",
    ),
  );

  bindHighlight(plot, (active, pinned) => {
    const group = model.groups.find((candidate) => candidate.key === active);
    for (const marker of markers) {
      const { key } = marker.dataset;
      marker.classList.toggle("is-active", key === active);
      marker.setAttribute("aria-pressed", String(key === pinned));
    }
    readout.textContent = group ? descriptions.get(active) : hint;
    const showLabel = group && !model.labels.has(active);
    activeLabel.hidden = !showLabel;
    if (showLabel) {
      positionAt(activeLabel, group.x, group.y);
      activeLabel.className = `scatter-label ${activeLabelSide(group.y)} align-${labelAlignment(group.x)}`;
      activeLabel.textContent = group.points.map((point) => point.item_id).join(", ");
    }
  });
  bindArrowNavigation(plot, markers);
  return chart;
}
