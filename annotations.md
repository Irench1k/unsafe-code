### Unsafe tutorial annotations

This document specifies the current annotation format and README generation flow. It replaces the older, complex proposal; ignore any legacy ideas.

### Goals
- Keep annotations close to code for discoverability and correctness
- Make README creation deterministic and maintainable
- Support multi-part examples, cross-file blocks, and multiple languages

### Inline annotation format
- Open marker: `@unsafe[function]` or `@unsafe[block]` inside a language comment
- YAML metadata follows marker, until a closing line `@/unsafe`
- For multi-part blocks, additional parts use `@unsafe[block]` with only `id` and `part`, then `@/unsafe`. No other fields in non-first parts
- A closing marker `@/unsafe[block]` MUST appear in code later to delimit the block’s quoted code segment. One such terminator closes the preceding block part only

Supported fields (YAML):
- `id` (integer, required)
- `title` (string, optional)
- `notes` (string, optional, Markdown allowed; `|` block scalars permitted)
- `request-details` (string, optional: `open` to expand HTTP <details>)
- `part` (integer ≥1, only for block; if omitted, defaults to 1)

Semantics:
- `[function]` applies to the function/method immediately following the annotation. The quoted code begins at the first decorator above the function (if present) or the `def`/`async def` line, and ends at the end of that function (right before the next top‑level definition/decorator). One part only. Duplicate ids for function examples are an error
- `[block]` spans arbitrary code starting right after the `@/unsafe` metadata closer and ending right before the next `@/unsafe[block]` terminator line in the same file. Blocks may have multiple parts across one or more files; parts with the same `id` are merged in ascending `part` order. Only part 1 carries metadata; later parts must not override it

Quoting rules:
- For `[function]`: code span = decorators (if any) + def through the end of the function body, determined by Python indentation (or analogous boundaries for other languages)
- For `[block]`: code span = from the first non-empty line after `@/unsafe` until the line before the matching `@/unsafe[block]`
- Notes allow Markdown including fenced blocks. Indentation of block scalars is preserved (dedented by common leading spaces)

### readme.yml format
Top-level fields:
- `title` (string) — README title
- `intro` (string) — intro paragraph(s)
- `category` (string, optional)
- `id-prefix` (string, optional)
- `structure` (list): mixed entries
  - `{ table-of-contents: true }` renders an auto TOC, ordered by subsequent sections and their `examples`
  - Section entries: `{ section: "Section Title", description?: "...", examples: [ids...] }`

### Layout conventions
- Images: `images/image-{id}.png`
- HTTP requests: `http/exploit-{id}.http`
- Not all examples need attachments; extras in folders are ignored

### Index cache (index.yml)
Per directory with `readme.yml` we store an index with:
- Examples (id, kind, title, notes, request_details, parts with file and [start,end] spans)
- File hashes for all participating files
- Attachments with sha256
- `build_signature` = SHA256 over example fingerprints + attachment hashes
- `last_readme_fingerprint` updated after generation; if unchanged next run, README generation is skipped

### Generation flow
1) Parse `readme.yml` into the desired structure
2) Discover `@unsafe` annotations across `*.py, *.js, *.ts, *.tsx, *.jsx` inside the target directory subtree only
3) Build `index.yml`: merge block parts by id, validate function ids uniqueness, compute per‑part code spans using the annotation boundaries (no route or pattern sniffing), compute file hashes and signatures, pick anchor path and [start,end] from function span (for blocks, from the first part)
4) Render README.md from the index and structure
   - TOC includes id, section as Category, and a link to the anchored file with `#Lstart-Lend`
   - Example section prints title, notes, a code snippet composed by concatenating all parts’ spans in order, HTTP request (if exists, inside <details> and opened when `request-details: open`), and image (if exists)

### Multi-language support
- Comments are recognized in Python (`# ...`), JS/TS single-line (`// ...`) and standalone `/* ... */` marker lines
- Function boundary identification is implemented for Python; best-effort for others (future work)

### Authoring rules of thumb
- Prefer `[function]` for single-function examples; use `[block]` for flows spanning multiple functions/files
- Only part 1 carries metadata; keep texts concise, Markdown okay
- Use stable numeric ids; avoid reusing ids across unrelated examples

### Known behavior
- Exact code spans are best-effort within the language rules; for Python we anchor to the decorators/def and end at the next top‑level definition. For blocks we require `@/unsafe[block]` to delimit the span
