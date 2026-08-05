/**
 * Preprocess OCR result text for better markdown rendering.
 * - Wraps standalone LaTeX environments in $$ delimiters for KaTeX
 * - Normalizes whitespace
 */

const LATEX_ENVS = [
  "tabular",
  "array",
  "align",
  "aligned",
  "equation",
  "gather",
  "gathered",
  "matrix",
  "bmatrix",
  "pmatrix",
  "vmatrix",
  "Vmatrix",
  "cases",
  "split",
  "multline",
];

const LATEX_ENV_PATTERN = new RegExp(
  `(\\\\begin\\{(${LATEX_ENVS.join("|")})\\*?\\}[\\s\\S]*?\\\\end\\{\\2\\*?\\})`,
  "g"
);

/**
 * Remove model "thinking" so it shows only in the Raw view, never Rendered.
 * - Strips complete <think>...</think> blocks.
 * - During streaming, an unclosed <think> means thinking is in progress, so
 *   everything from it onward is hidden until the closing tag arrives.
 */
export function stripThinking(text: string): string {
  if (!text) return text;
  let out = text.replace(/<think>[\s\S]*?<\/think>\s*/gi, "");
  const open = out.search(/<think>/i);
  if (open !== -1) out = out.slice(0, open);
  return out;
}

export function preprocessOcrText(text: string): string {
  // Wrap standalone LaTeX environments in $$ for KaTeX rendering
  text = text.replace(LATEX_ENV_PATTERN, (match, _block, _env, offset) => {
    const before = text.substring(Math.max(0, offset - 5), offset).trim();
    if (before.endsWith("$$")) return match;
    return `$$\n${match}\n$$`;
  });

  return text;
}
