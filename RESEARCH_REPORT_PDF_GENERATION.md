# Research Report PDF Generation — Exact Reproduction Instructions

This document tells any future Claude session exactly how to turn a research `.md` report into a PDF that matches a clean, academic "house style" perfectly. It is domain-agnostic: use it for any Markdown research document, technical report, or internal write-up. Follow every step in order.

Throughout this guide, replace the placeholder tokens with values for your specific document:

- `<REPORT_TITLE>` — the report's title (e.g. project or system name)
- `<REPORT_SUBTITLE>` — the one-line descriptor (e.g. "Internal Research Report")
- `<MONTH_YEAR>` — the date shown in the running header (e.g. "May 2026")
- `<VERSION>` — a version string if the document is versioned (optional)

---

## 1. What You Are Reproducing

The target output is a LaTeX-compiled PDF using Computer Modern fonts — the same typeface family used by the ACM, IEEE, and most academic publishers. It is **not** a styled HTML export, not a Pandoc conversion, not a Word doc. It is native LaTeX, compiled with `pdflatex`. This matters because Computer Modern fonts are only available at full quality through a TeX compiler.

**Measured specs of the target format (extracted from reference PDFs in this style):**

| Property | Value |
|---|---|
| Page size | US Letter — 612 × 792 pts (215.9 × 279.4 mm) |
| Left margin | 71.6 pts (≈ 25.3 mm / 1 inch) |
| Right margin | 70.0 pts (≈ 24.7 mm / 1 inch) |
| Top margin | 0.9 in (header sits at y = 29.4 pts from top) |
| Bottom margin | 0.9 in (footer page number at y ≈ 750 pts) |
| Body font | CMR10 — Computer Modern Roman 10pt |
| Body font size rendered | 10.0 pt (11pt in \normalsize at 10pt base = 10.95pt — use 10pt class) |
| Title font | CMBX12 — Computer Modern Bold Extended 12pt (renders at 17.2pt for \LARGE) |
| Section heading font | CMBX10 — Computer Modern Bold 10pt |
| Subsection heading font | CMBX10 — 10pt bold |
| Subsubsection heading font | CMBXTI10 — Computer Modern Bold Italic 10pt |
| Italic text | CMTI10 — Computer Modern Italic 10pt |
| Monospace / code | CMTT10 — Computer Modern Typewriter 10pt |
| Math roman | CMR10/CMR7 |
| Math italic | CMMI10/CMMI7 |
| Math symbols | CMSY10/CMSY7 |
| Math extension | CMEX10 |
| Header text size | CMR9 — 9pt (via `\small` in fancyhdr) |
| Header left | `<MONTH_YEAR>` (e.g. "May 2026") |
| Header center | `<REPORT_TITLE> --- <REPORT_SUBTITLE>` |
| Header right | (empty) |
| Footer center | Page number (Arabic numeral) |
| Paragraph spacing | 4pt (via `\setlength{\parskip}{4pt}`) |
| Paragraph indent | 0pt (no first-line indent) |
| Line spacing | Single (no setspace adjustments) |

---

## 2. Verify the Environment First

Before writing any LaTeX, run this check:

```bash
which pdflatex && pdflatex --version | head -1
```

Expected output: something like `pdfTeX 3.141592653-2.6-1.40.25 (TeX Live 2023/Debian)`. If `pdflatex` is not found, the rest will not work — do not proceed.

---

## 3. The LaTeX Preamble (Copy Exactly)

This preamble encodes all the font, margin, header, and section formatting decisions. Do not change it except for the header strings on the lines marked `CHANGE THIS`.

```latex
\documentclass[10pt]{article}
\usepackage[margin=1in, top=0.9in, bottom=0.9in]{geometry}
\usepackage{amsmath, amssymb, amsfonts}
\usepackage[protrusion=true,expansion=false]{microtype}
\usepackage{fancyhdr}
\usepackage{booktabs}
\usepackage{array}
\usepackage{longtable}
\usepackage{parskip}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\small <MONTH_YEAR>}                                  % CHANGE THIS
\fancyhead[C]{\small <REPORT_TITLE> --- <REPORT_SUBTITLE>}          % CHANGE THIS
\fancyfoot[C]{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0pt}

\usepackage{titlesec}
\titleformat{\section}[block]{\large\bfseries}{}{0pt}{}[\vspace{-6pt}\rule{\linewidth}{0.8pt}]
\titlespacing{\section}{0pt}{14pt}{6pt}
\titleformat{\subsection}[hang]{\normalsize\bfseries}{}{0pt}{}
\titlespacing{\subsection}{0pt}{10pt}{3pt}
\titleformat{\subsubsection}[hang]{\normalsize\bfseries\itshape}{}{0pt}{}
\titlespacing{\subsubsection}{0pt}{8pt}{2pt}

\setlist[itemize]{noitemsep, topsep=3pt, parsep=0pt, partopsep=0pt, leftmargin=1.5em}
\setlist[enumerate]{noitemsep, topsep=3pt, parsep=0pt, partopsep=0pt, leftmargin=2em}

\setlength{\parskip}{4pt}
\setlength{\parindent}{0pt}
```

**Critical note on microtype:** The line must say `expansion=false`. Using plain `\usepackage{microtype}` will cause a fatal `pdfTeX error (font expansion): auto expansion is only possible with scalable fonts` error mid-document and produce no output. This is a common root cause of compilation failure with Computer Modern (bitmap) fonts.

---

## 4. Title Block Structure

Always use this exact structure at the top of `\begin{document}`. Fill the placeholders from the `.md` front matter; drop any metadata line the document doesn't have.

```latex
\begin{center}
{\LARGE\textbf{<REPORT_TITLE>}}\\[4pt]
{\large <REPORT_SUBTITLE>}\\[4pt]
{\normalsize\textit{<subtitle line 1>\\
<subtitle line 2>\\
<subtitle line 3>}}\\[8pt]
\rule{\linewidth}{0.4pt}\\[3pt]
\textbf{Status:} <status text> \quad \textbf{Date:} <date>\\
\textbf{Version:} <version info>\\
\rule{\linewidth}{0.4pt}
\end{center}
```

The two `\rule{\linewidth}{0.4pt}` lines produce the thin horizontal rules flanking the metadata block. Do not replace with `\hrule` — the width is wrong. The metadata rows (Status / Date / Version, or whatever the document provides) are optional; keep only the ones that apply.

---

## 5. Section and Heading Conventions

| Markdown level | LaTeX command | Rendered font |
|---|---|---|
| `# TITLE` | `\section{TITLE}` | CMBX12 large, underlined with rule |
| `## Subsection` | `\subsection{Subsection}` | CMBX10 bold |
| `### Sub-subsection` | `\subsubsection{Sub-subsection}` | CMBXTI10 bold italic |

Section headings automatically get a horizontal rule underneath them via the `titlesec` configuration. Do not add `---` or `***` manually.

---

## 6. Math Formatting Rules

All inline math uses `$...$`. All display equations use either `\begin{equation}...\end{equation}` (numbered) or `\begin{align}...\end{align}` (multi-line, numbered) or `\begin{align*}...\end{align*}` (unnumbered).

**Key operator conventions (use these whenever the document contains named functions):**

```latex
\operatorname{softmax}        % not \text{softmax} — renders upright in math
\operatorname{sim}            % similarity function
\operatorname{Attention}      % named function
\bigl[ ... \bigr]             % sized brackets for multi-term arguments
\exp\!\bigl(...\bigr)         % tight spacing before \bigl
\quad                         % space between equation and condition label
```

**Subscript/superscript text convention:**

```latex
h_{\text{pos}}                % text subscripts use \text{}
h_{\text{anc}}
\mathcal{L}_{\text{contrast}} % calligraphic with text subscript
```

**Multi-line aligned equations (illustrative pattern):**

```latex
\begin{align}
  a_{\text{ext}} &= \bigl[a_{\text{seq}};\; a_{\text{corr}}\bigr] \\[4pt]
  b_{\text{ext}} &= \bigl[b_{\text{seq}};\; b_{\text{corr}}\bigr] \\[8pt]
  s_{\text{seq}} &= Q K_{\text{seq}}^\top / \sqrt{d} \nonumber\\
  \text{output}  &= \operatorname{softmax}(\ldots) \cdot b_{\text{ext}}
\end{align}
```

The `\\[4pt]` and `\\[8pt]` add visual breathing room between groups within an align block. The `\nonumber` suppresses equation numbers on intermediate lines.

---

## 7. Tables

Always use `booktabs` style. Never use `\hline`. The three commands are `\toprule`, `\midrule`, `\bottomrule`.

```latex
\begin{center}
\renewcommand{\arraystretch}{1.3}
\begin{tabular}{p{3.5cm}p{3.8cm}p{4.7cm}}
\toprule
\textbf{Column 1} & \textbf{Column 2} & \textbf{Column 3} \\
\midrule
content & content & content \\
\bottomrule
\end{tabular}
\end{center}
```

**Column widths for 3-column tables on this page width:**
- Narrow label col: `p{2.8cm}` or `p{3.5cm}`
- Medium col: `p{3.8cm}` or `p{4.0cm}`
- Wide content col: `p{4.7cm}` or `p{5.2cm}`
- The three widths must sum to ≤ 12cm to fit within the 470pt text width with padding.

`\arraystretch{1.3}` gives rows comfortable vertical breathing room. Always set it for content tables.

---

## 8. Lists

```latex
% Itemize
\begin{itemize}
  \item \textbf{Label:} Content text.
  \item Content text.
\end{itemize}

% Enumerate
\begin{enumerate}
  \item First step.
  \item Second step.
\end{enumerate}
```

The `enumitem` package with the settings in the preamble handles compact spacing automatically. Do not add manual `\vspace` inside lists.

---

## 9. Inline Code and Monospace

```latex
\texttt{requires\_grad = False}    % inline code/variable names
\texttt{natural\_language\_description}
```

Note: underscores inside `\texttt{}` must be escaped as `\_`.

---

## 10. Compilation Procedure

Save the `.tex` file, then run:

```bash
pdflatex -interaction=nonstopmode yourfile.tex
```

Run it **twice** if the document has cross-references or a table of contents (the second pass resolves forward references). For a report with no TOC and no `\ref` cross-references, one pass is sufficient.

**Interpreting output:**
- `Output written on yourfile.pdf (N pages, XXXXX bytes).` = success
- `! pdfTeX error (font expansion)` = you used plain `\usepackage{microtype}`. Fix: change to `\usepackage[protrusion=true,expansion=false]{microtype}`.
- `! Undefined control sequence` = a LaTeX command typo. Read the line number.
- `Overfull \hbox` warnings = minor line overflow, not fatal, output still produced.
- `Fatal error occurred, no output PDF file produced!` = actual failure. Read the log.

**View the log for details:**

```bash
cat yourfile.log | grep -E "error|Error|fatal|Fatal" | head -20
```

---

## 11. Converting the Markdown to LaTeX — Mapping Table

When given a new `.md` report, apply these conversions systematically:

| Markdown | LaTeX |
|---|---|
| `# TITLE` | `\section{TITLE}` |
| `## Heading` | `\subsection{Heading}` |
| `### Heading` | `\subsubsection{Heading}` |
| `**bold text**` | `\textbf{bold text}` |
| `*italic text*` | `\textit{italic text}` |
| `` `code` `` | `\texttt{code}` (escape underscores as `\_`) |
| `$$...$$` display math | `\begin{equation}...\end{equation}` |
| `$...$` inline math | `$...$` (unchanged) |
| `---` horizontal rule | `\rule{\linewidth}{0.4pt}` (in title block only) |
| `---` section separator | Not needed — `\section{}` adds its own rule |
| Markdown table | `booktabs` tabular (see Section 7) |
| `- item` | `\item` inside `itemize` |
| `1. item` | `\item` inside `enumerate` |
| `\n\n` paragraph break | Blank line in LaTeX (same behavior) |
| Em dash `—` | `---` in LaTeX source |
| `~` tilde (non-breaking space) | `~` in LaTeX (unchanged) |
| `...` ellipsis | `\ldots` in math, `\ldots{}` or `\dots` in text |

---

## 12. What NOT to Do

| Wrong approach | Why it fails |
|---|---|
| Export HTML then print to PDF | Produces system fonts (Arial, Helvetica), not Computer Modern. Font mismatch is immediately visible. |
| Use Pandoc to convert .md → .pdf directly | Pandoc's default LaTeX template uses different margins, different section formatting, no `fancyhdr` header. Output looks different. |
| Use `\usepackage{microtype}` without `expansion=false` | Fatal pdfTeX crash mid-document with bitmap fonts. No PDF output. |
| Use `\hline` in tables | Produces thick, old-style rules. Incompatible with `booktabs` aesthetic. |
| Use `\text{softmax}` instead of `\operatorname{softmax}` | Minor but: `\text{}` doesn't add proper operator spacing in math mode. |
| Put code/variable names in the body without `\texttt{}` | Renders in serif Roman, not monospace. Looks wrong. |
| Skip the double `\rule{\linewidth}` in title block | The flanking rules around the metadata block are part of the identity. |

---

## 13. Quick-Start Checklist for a New Report

Given a new `.md` file, do this in order:

1. Confirm `pdflatex` is available (`which pdflatex`)
2. Copy the preamble from Section 3 exactly
3. Update the header strings (`\fancyhead[L]` and `\fancyhead[C]`) with the report's date, title, and subtitle
4. Build the title block (Section 4) from the `.md` front matter
5. Convert all `#` → `\section`, `##` → `\subsection`, `###` → `\subsubsection`
6. Convert all bold/italic/code/math per the mapping table (Section 11)
7. Convert all Markdown tables to `booktabs` tabular (Section 7)
8. Run `pdflatex -interaction=nonstopmode yourfile.tex`
9. Check for `Output written on ... (N pages` in the last line
10. Copy the output PDF to the designated outputs directory and deliver it to the user

---

## 14. Reference Files

Keep the source `.md` and any known-good reference PDF together so the style can always be checked and regenerated:

| File | Purpose |
|---|---|
| Reference PDF (known-good output) | Visual reference — what the output should look like |
| Source `.md` (content) | The fully-written source document |
| Original reference PDF (optional) | The document whose formatting this style was reverse-engineered from |

The `.tex` source does not need to be preserved between sessions — it can always be regenerated from the `.md` using these instructions. The PDF itself is the ground truth for the visual style.

---

*General-purpose instructions for reproducing a Computer Modern / LaTeX house style from any Markdown research document.*
