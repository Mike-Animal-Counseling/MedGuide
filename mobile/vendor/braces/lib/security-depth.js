"use strict";
module.exports = function guardAst(ast) {
  const stack = [[ast, 0]], seen = new Set(); let count = 0;
  while (stack.length) {
    const [node, depth] = stack.pop();
    if (!node || typeof node !== 'object' || seen.has(node) || depth > 128 || ++count > 10000) throw new SyntaxError('Brace AST exceeds safe limits');
    seen.add(node);
    if (node.nodes) { if (!Array.isArray(node.nodes)) throw new SyntaxError('Invalid brace AST'); for (const child of node.nodes) stack.push([child, depth + 1]); }
  }
};
