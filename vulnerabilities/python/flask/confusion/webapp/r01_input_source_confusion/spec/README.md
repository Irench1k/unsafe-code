# r01 spec suite

- `common.http`: shared variables/helpers (no `@name` so imports are global).
- `v10x/*.http`: endpoint-focused specs per version (one file per route group).
  - Tags: `spec,v10x,<endpoint>` (e.g., `spec,v103,cart`).
  - JS helpers prefer `response.parsedBody` for assertions to avoid env differences.
- Tests assume the backing data has enough balance to place at least one order; reset seed data if you hit `Insufficient balance` (see guard in `v101/orders.http`).

Run examples:

- Single file: `httpyac send r01_input_source_confusion/spec/v103/cart.http --all`
- Whole version: `httpyac send 'r01_input_source_confusion/spec/v104/*.http' --all --bail`
