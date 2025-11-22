# httpYac Collections (r01–r03)

Student-facing exploit docs stay under `r0X_* /http/e*/`. Automation-minded e2e specs now live under `r0X_*/spec/`, organized by version and endpoint with minimal storytelling.

## Working subset of httpYac features we use

- Global variables/helpers via `spec/common.http` (no `@name` so imports work): base host, actors, token/email helpers.
- Metadata: `@tag` for filtering by version/area (e.g., `spec,v101,orders`), `@name` only when a response is reused, `@ref` only for true dependencies.
- Assertions: `??` shorthands plus `?? js ...` for computed checks. Prefer structural assertions over string matching.

## Structure & usage (r01 example)

- `r01_input_source_confusion/spec/common.http` — shared vars/helpers.
- `r01_input_source_confusion/spec/v101/` — one file per endpoint (`menu.http`, `account.http`, `orders.http`, ...).
- Repeat per version (v102–v107) so every route is checked in every lifecycle step.
- Run a slice: `httpyac send r01_input_source_confusion/spec/v103/cart.http --all`
- Run a whole version: `httpyac send "r01_input_source_confusion/spec/v103/*.http" --all --bail`

Expect many failures today—the specs encode desired secure behavior. Fix code later; for now they should surface every gap without syntax/runner errors.
