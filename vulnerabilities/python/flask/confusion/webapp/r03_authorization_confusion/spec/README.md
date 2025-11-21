# r03 spec suite

- `common.http` defines host/admin key + actors.
- Each version has `_reset.http` to re-run schema fixtures via `/platform/reset` (and `/platform/balance` to top up users).
- Specs should `@ref` the reset before any assertions to keep runs deterministic.

Run examples:
- `httpyac send r03_authorization_confusion/spec/v301/orders.http --all`
- `httpyac send "r03_authorization_confusion/spec/v3*/_reset.http" --all` to verify reset endpoints respond.
