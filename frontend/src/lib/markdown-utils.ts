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

export function preprocessOcrText(text: string): string {
  // Wrap standalone LaTeX environments in $$ for KaTeX rendering
  text = text.replace(LATEX_ENV_PATTERN, (match, _block, _env, offset) => {
    const before = text.substring(Math.max(0, offset - 5), offset).trim();
    if (before.endsWith("$$")) return match;
    return `$$\n${match}\n$$`;
  });

  return text;
}
