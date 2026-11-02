// Textos do relatório vêm de arquivos do usuário: entram sempre como nós de
// texto, nunca como HTML.
function fill(node, attributes, children) {
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, value);
  node.append(...children.filter((child) => child !== null && child !== undefined));
  return node;
}

export function el(tag, attributes = {}, ...children) {
  return fill(document.createElement(tag), attributes, children);
}

export function svg(tag, attributes = {}, ...children) {
  return fill(document.createElementNS("http://www.w3.org/2000/svg", tag), attributes, children);
}
