"""AST-based augmentation for backend results.

Any backend's ExtractionResult can be enriched with Python AST analysis
to fill gaps that the backend can't handle natively. This is the key
insight: each backend has unique strengths (Joern's call graph, CodeQL's
type inference), but ALL backends struggle with the same Python-specific
patterns (decorator semantics, parameter aliases, ternary source selection).

The AST augmenter fills these gaps without replacing what the backend
already found — it only ADDS missing information.
"""

from __future__ import annotations

from pathlib import Path

from ..models import InputAccessFact, RouteFact
from .ast_backend import ASTBackend
from .interface import ExtractionResult


def augment_with_ast(
    result: ExtractionResult,
    target: Path,
    fill_routes: bool = True,
    fill_accesses: bool = True,
    fill_call_edges: bool = True,
    fill_before_requests: bool = True,
    fill_dict_merges: bool = True,
) -> ExtractionResult:
    """Augment backend results with AST analysis to fill gaps.

    For each fact type, the augmenter only adds facts that the backend
    didn't find. It uses handler qualname matching to avoid duplicates.

    This allows each backend to contribute its unique strengths while
    AST fills the gaps from Python-specific patterns.
    """
    ast_result = ASTBackend().extract(target)

    routes = list(result.routes)
    accesses = list(result.input_accesses)
    edges = list(result.call_edges)
    before_requests = list(result.before_requests)
    dict_merges = list(result.dict_merges)

    if fill_routes:
        existing_handlers = {r.handler_qualname for r in routes}
        # Secondary check by (handler_name, rule) for backends with different qualname formats
        existing_name_rule = {(r.handler_name, r.rule or "") for r in routes}
        for r in ast_result.routes:
            if r.handler_qualname in existing_handlers:
                _update_route_metadata(routes, r)
            elif (r.handler_name, r.rule or "") in existing_name_rule:
                pass  # Same route under different qualname format — skip
            else:
                routes.append(r)

    if fill_accesses:
        existing = {
            (a.function_qualname, a.key_literal, a.source.value, a.accessor.value)
            for a in accesses
        }
        for a in ast_result.input_accesses:
            key = (a.function_qualname, a.key_literal, a.source.value, a.accessor.value)
            if key not in existing:
                accesses.append(a)

    if fill_call_edges:
        existing_pairs = {(e.caller_qualname, e.callee_qualname) for e in edges}
        for e in ast_result.call_edges:
            if (e.caller_qualname, e.callee_qualname) not in existing_pairs:
                edges.append(e)

    if fill_before_requests and not before_requests:
        before_requests = list(ast_result.before_requests)

    if fill_dict_merges and not dict_merges:
        dict_merges = list(ast_result.dict_merges)

    return ExtractionResult(
        routes=routes,
        input_accesses=accesses,
        call_edges=edges,
        before_requests=before_requests,
        dict_merges=dict_merges,
    )


def _update_route_metadata(routes: list[RouteFact], ast_route: RouteFact) -> None:
    """Fill missing route metadata from the AST route.

    Fixes methods if the backend defaulted to GET, and always fills in
    missing blueprint and raw_code values.
    """
    for i, r in enumerate(routes):
        if r.handler_qualname != ast_route.handler_qualname:
            continue

        # Determine if any field needs updating
        needs_method_fix = r.methods == ("GET",) and ast_route.methods != ("GET",)
        needs_blueprint = not r.blueprint and ast_route.blueprint
        needs_raw_code = not r.raw_code and ast_route.raw_code

        if needs_method_fix or needs_blueprint or needs_raw_code:
            routes[i] = RouteFact(
                handler_name=r.handler_name,
                handler_qualname=r.handler_qualname,
                route_kind=r.route_kind,
                rule=r.rule,
                methods=ast_route.methods if needs_method_fix else r.methods,
                blueprint=r.blueprint or ast_route.blueprint,
                location=r.location,
                raw_code=r.raw_code or ast_route.raw_code,
                notes=r.notes,
            )
