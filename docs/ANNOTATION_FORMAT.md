### Unsafe tutorial annotations

This document specifies the annotation format and README generation flow. It reflects the current strict, simple, contributor‑friendly design.

### Goals
- Keep annotations close to the code (refactor‑proof)
- Use a minimal, intuitive schema with early, clear errors
- Support multi‑part examples, cross‑file blocks, and multiple languages

### Fenced annotations (inline)
- Open marker: `@unsafe[function]` or `@unsafe[block]`
- YAML metadata follows the marker until a closing line `@/unsafe`
- For blocks only, the quoted code span ends at the next `@/unsafe[block]` in the same file

Notes:
- Place markers inside comments for readability (recommended), but the parser does not enforce this.
- The closing `@/unsafe` is mandatory; missing closers are hard errors.

Supported YAML fields (strict):
- `id` (int, required)
- `title` (string, optional)
- `notes` (string, optional; Markdown allowed)
- `http` (string, optional: `open` | `closed`, default `closed`) — whether the HTTP request block in README is expanded
- `part` (int ≥ 1, only for block; defaults to 1)

Semantics:
- `[function]` applies to the next function/method. Quoted code begins at the first decorator above the function (if any) or the `def`/`async def` line and ends at the end of the function body. It is single‑part. Duplicate ids for function examples are errors.
- `[block]` spans arbitrary code from immediately after `@/unsafe` to the line before the next `@/unsafe[block]`. Blocks may have multiple parts across files; parts with the same `id` are merged in ascending `part` order. Only part 1 may include `title`, `notes`, `http`.

Quoting rules:
- Function: decorators (if present) + `def` line through end of the function body (Python AST‑assisted; brace/indent heuristics for others)
- Block: from the first non‑empty line after `@/unsafe` to the line before the matching `@/unsafe[block]`
- Notes allow Markdown including fenced code blocks (```…```). Indentation within YAML block scalars is normalized for stable rendering.

### readme.yml format (strict)
Top-level fields:
- `title` (string) — README title
- `summary` (string) — short summary (used in higher-level indices)
- `description` (string) — extended preamble (can include headings like `## Overview`)
- `category` (string, optional)
- `namespace` (string, optional; future‑proof id namespace)
- `toc` (bool) — whether to render a Table of Contents for examples
- `outline` (list of sections): each item is `{ title: "Section Title", description?: "...", examples: [ids...] }`

Uniform outline entries only; no special ToC entries. If `toc: true`, the ToC is rendered implicitly after the intro.

### Layout conventions
- Images: `images/image-{id}.png`
- HTTP requests: `http/exploit-{id}.http`
- Attachments are optional; extra files are ignored.

### Index cache (index.yml)
Per directory with a `readme.yml` we store an index with:
- Examples (id, kind, title, notes, http, language, parts with file and [start,end] spans)
- File hashes for all participating files
- Attachments with sha256
- `build_signature` = SHA256 over example fingerprints + attachment hashes
- `last_readme_fingerprint` updated after generation; if unchanged, README generation is skipped

### Generation flow
1) Parse `readme.yml` strictly (unknown keys are errors)
2) Discover `@unsafe` annotations under the target directory subtree
3) Build `index.yml`: merge block parts by id, validate kinds/parts, compute spans and hashes
4) Render README.md from the index and outline
   - ToC includes id, section (Category), and a link to the first part's file with `#Lstart-Lend`
   - Each example prints title, notes, concatenated code (with blank lines between parts), HTTP request (if present; open when `http: open`), and image (if present)

### Multi-language support
- Function boundary identification is implemented for Python; best‑effort for JS/TS
- Comment styles are recognized for YAML extraction but are not strictly required for markers

### Authoring tips
- Prefer `[function]` for single functions; use `[block]` for flows spanning multiple functions/files
- Only part 1 carries metadata; keep texts concise
- Use stable numeric ids across edits

### YAML style for Markdown
Use folded style (`>` or `>-`) for multi‑line Markdown blocks when convenient. The generator normalizes paragraphs and preserves fenced code blocks, so either `|` (literal) or `>` (folded) works — prefer readability.
