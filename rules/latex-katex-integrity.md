<!-- Copyright Gint Atkinson, gint.atkinson@gmail.com -->

# Rule: LaTeX & KaTeX Mathematical Rendering Integrity

**ALWAYS enforce:** Mathematical formulas and equations across all specification documents, requirements, architecture documentation, and codebase artifacts MUST strictly conform to KaTeX / LaTeX parsing and rendering integrity standards.

## Normative Constraints

- **Multi-Line Aligned Display Math Blocks**: Multi-line aligned display math blocks MUST use `\begin{aligned} ... \end{aligned}` enclosed in `$$` delimiters placed on dedicated newlines.
- **Forbidden Bare Alignment Operators**: The alignment operator (`&`) is strictly forbidden outside an explicit alignment/tabular environment (`aligned`, `matrix`, `bmatrix`, `pmatrix`, `cases`, `array`). Bare `&` characters in math mode cause parser crashes in KaTeX.
- **Prohibition of Top-Level `align` / `align*` in Markdown Math Mode**: Top-level `\begin{align}` and `\begin{align*}` environments are strictly prohibited inside markdown `$$ ... $$` math blocks. Authors MUST use `\begin{aligned} ... \end{aligned}` within `$$ ... $$` instead.
- **Inline Math Scope and Currency Escaping**: Inline math MUST use single `$...$` or `\(...\)` on a single line and must not span multiple paragraphs. Any literal currency dollar signs or non-math dollar symbols MUST be escaped as `\$`.
- **Balanced Display Math Delimiters**: Opening and closing `$$` blocks MUST be strictly balanced, and display math delimiters `$$` MUST reside on isolated, dedicated lines.

## Why

Markdown rendering engines (such as GitHub, web portals, and documentation generators) utilize KaTeX / MathJax to parse equations. KaTeX renders expressions directly in math mode inside `$$ ... $$` delimiters:
1. `\begin{align}` and `\begin{align*}` are LaTeX document-level environments incompatible with math mode and trigger KaTeX parse errors.
2. Unenclosed alignment tabs (`&`) cause fatal syntax errors unless wrapped in an alignment environment such as `aligned`.
3. Unbalanced `$$` delimiters or unescaped currency literals break subsequent markdown formatting, swallowing text and invalidating downstream documentation parsers.
