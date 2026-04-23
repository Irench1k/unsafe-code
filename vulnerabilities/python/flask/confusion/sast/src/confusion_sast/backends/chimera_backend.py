"""Chimera backend: combines AST, Joern, and CodeQL for maximum coverage.

Strategy:
- AST backend provides the baseline: route detection, source propagation
  through function parameters, ternary alias resolution, dict merge
  detection, before_request middleware detection. These are Python-specific
  patterns where pure AST is most precise.

- Joern adds: richer interprocedural call graph edges, `data.get("key")`
  accessor detection in helper functions (without needing to resolve the
  source through parameter propagation).

- CodeQL adds: type-aware route detection via Flask library models,
  direct `request.attr.get("key")` detection.

The chimera merges facts from all available backends, deduplicating by
(function_qualname, key, source, accessor) for accesses and
(handler_qualname, rule) for routes.

Usage:
    confusion-scan target/ --backend chimera
    confusion-scan target/ --backend chimera --debug
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from ..models import (
    BeforeRequestFact,
    CallEdge,
    DictMergeFact,
    InputAccessFact,
    RouteFact,
)
from .ast_backend import ASTBackend
from .interface import ExtractionResult


class ChimeraBackend:
    """Combines AST + Joern + CodeQL for maximum extraction coverage."""

    name = "chimera"

    def __init__(self, debug: bool = False, backends: list[str] | None = None) -> None:
        self._debug = debug
        self._backend_names = backends or ["ast", "joern"]

    def extract(self, target: Path) -> ExtractionResult:
        target = Path(target).resolve()
        all_results: dict[str, ExtractionResult] = {}

        for name in self._backend_names:
            t0 = time.monotonic()
            try:
                backend = _make_backend(name, self._debug)
                all_results[name] = backend.extract(target)
                elapsed = time.monotonic() - t0
                if self._debug:
                    r = all_results[name]
                    print(
                        f"[chimera] {name}: {len(r.routes)} routes, "
                        f"{len(r.input_accesses)} accesses, "
                        f"{len(r.call_edges)} edges ({elapsed:.1f}s)",
                        file=sys.stderr,
                    )
            except Exception as e:
                if self._debug:
                    print(f"[chimera] {name} failed: {e}", file=sys.stderr)

        if not all_results:
            raise RuntimeError("All backends failed")

        return self._merge_results(all_results)

    def _merge_results(self, results: dict[str, ExtractionResult]) -> ExtractionResult:
        """Merge extraction results, preferring more detailed facts."""
        routes: list[RouteFact] = []
        accesses: list[InputAccessFact] = []
        edges: list[CallEdge] = []
        before_requests: list[BeforeRequestFact] = []
        dict_merges: list[DictMergeFact] = []

        seen_routes: set[tuple] = set()
        seen_accesses: set[tuple] = set()
        seen_edges: set[tuple] = set()

        # Process backends in priority order: AST first (most detailed for routes),
        # then Joern (best call graph), then CodeQL (type-aware)
        priority_order = ["ast", "joern", "codeql"]
        ordered = sorted(results.items(), key=lambda kv: priority_order.index(kv[0]) if kv[0] in priority_order else 99)

        for name, result in ordered:
            # Routes: deduplicate by (handler_qualname, rule) to distinguish
            # same-named handlers across exercises/modules
            for r in result.routes:
                key = (r.handler_qualname, r.rule or "")
                if key not in seen_routes:
                    seen_routes.add(key)
                    routes.append(r)
                else:
                    # If existing route has default GET but this one has real methods, update
                    for i, existing in enumerate(routes):
                        existing_key = (existing.handler_qualname, existing.rule or "")
                        if existing_key == key and existing.methods == ("GET",) and r.methods != ("GET",):
                            routes[i] = RouteFact(
                                handler_name=existing.handler_name,
                                handler_qualname=existing.handler_qualname,
                                route_kind=existing.route_kind,
                                rule=existing.rule or r.rule,
                                methods=r.methods,
                                blueprint=existing.blueprint or r.blueprint,
                                location=existing.location,
                                raw_code=existing.raw_code or r.raw_code,
                            )

            # Accesses: deduplicate by (function_qualname, key_literal, source, accessor)
            # using full qualname to distinguish same-named functions across modules
            for a in result.input_accesses:
                key = (a.function_qualname, a.key_literal, a.source.value, a.accessor.value)
                if key not in seen_accesses:
                    seen_accesses.add(key)
                    accesses.append(a)

            # Edges: deduplicate by (caller_qualname, callee_qualname) using full qualnames
            for e in result.call_edges:
                key = (e.caller_qualname, e.callee_qualname)
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append(e)

            # Before requests and dict merges: take from first backend that has them
            if not before_requests and result.before_requests:
                before_requests = list(result.before_requests)
            if not dict_merges and result.dict_merges:
                dict_merges = list(result.dict_merges)

        if self._debug:
            print(
                f"[chimera] merged: {len(routes)} routes, {len(accesses)} accesses, "
                f"{len(edges)} edges",
                file=sys.stderr,
            )

        return ExtractionResult(
            routes=routes,
            input_accesses=accesses,
            call_edges=edges,
            before_requests=before_requests,
            dict_merges=dict_merges,
        )


def _make_backend(name: str, debug: bool):
    if name == "ast":
        return ASTBackend()
    elif name == "joern":
        from .joern_backend import JoernBackend
        return JoernBackend(debug=debug)
    elif name == "codeql":
        from .codeql_backend import CodeQLBackend
        return CodeQLBackend(debug=debug)
    raise ValueError(f"Unknown backend: {name}")
