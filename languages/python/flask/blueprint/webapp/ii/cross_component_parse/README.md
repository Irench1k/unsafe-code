# Cross-Component Parsing Drift in Flask
Decorators, middleware, and helpers sometimes grab request data before the view does; if each layer resolves parameters differently, the same call holds two meanings.
## Overview

Flask encourages reuse through decorators, before-request hooks, and helper modules. Each layer can inspect the request separately, but nothing guarantees they normalize or source parameters the same way. A guard might authenticate using `request.args` while the view trusts `request.form`, or a decorator may resolve `g.group` before another decorator has prepared it.

**Spotting the issue:** - Audit every decorator or middleware applied to a route and see which request APIs they touch. - Trace the order of decorators - Flask applies them bottom-up, so a guard may run before the state it relies on exists. - Be suspicious when global state (e.g. `g.*`) is set in one layer and consumed in another without a single source of truth.

These scenarios currently live under `confusion/parameter_source/` and will move here.

## Shared Contract Baseline
A safe reference flow where decorators and views agree on how the group identifier is sourced.

## Decorators That Drift
Guards implemented as decorators merge or prioritize request data differently than the view, enabling bypasses.

## Middleware Short-Circuiting Views
Before-request hooks authenticate on query parameters only, while views consume form data.
