"""Build and query the analysis graph from extracted facts.

The notebook UX depends on this module exposing precise, domain-specific
navigation primitives rather than forcing widgets to reconstruct that context
from the raw NetworkX graph. The graph remains a ``networkx.DiGraph`` for rule
authoring, but we preserve call-site metadata and provide summaries for
handlers, functions, edges, and findings-oriented traversal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

from ..backends.interface import ExtractionResult
from ..models import (
    BeforeRequestFact,
    CallEdge,
    DictMergeFact,
    InputAccessFact,
    RouteFact,
)
from ..rich_types import KeyAccessView, StatsView


@dataclass
class AnalysisGraph:
    """Queryable analysis graph built from extraction results."""

    g: nx.DiGraph
    target_root: Path | None
    call_edges: list[CallEdge]
    routes: list[RouteFact]
    input_accesses: list[InputAccessFact]
    before_requests: list[BeforeRequestFact]
    dict_merges: list[DictMergeFact]
    _accesses_by_func: dict[str, list[InputAccessFact]] = field(default_factory=dict, repr=False)
    _merges_by_func: dict[str, list[DictMergeFact]] = field(default_factory=dict, repr=False)
    _routes_by_handler: dict[str, list[RouteFact]] = field(default_factory=dict, repr=False)
    _before_by_blueprint: dict[str | None, list[BeforeRequestFact]] = field(
        default_factory=dict, repr=False
    )
    _calls_by_pair: dict[tuple[str, str], list[CallEdge]] = field(default_factory=dict, repr=False)
    _calls_by_caller: dict[str, list[CallEdge]] = field(default_factory=dict, repr=False)
    _calls_by_callee: dict[str, list[CallEdge]] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        for a in self.input_accesses:
            self._accesses_by_func.setdefault(a.function_qualname, []).append(a)
        for m in self.dict_merges:
            self._merges_by_func.setdefault(m.function_qualname, []).append(m)
        for r in self.routes:
            self._routes_by_handler.setdefault(r.handler_qualname, []).append(r)
        for b in self.before_requests:
            self._before_by_blueprint.setdefault(b.blueprint, []).append(b)
        for edge in self.call_edges:
            key = (edge.caller_qualname, edge.callee_qualname)
            self._calls_by_pair.setdefault(key, []).append(edge)
            self._calls_by_caller.setdefault(edge.caller_qualname, []).append(edge)
            self._calls_by_callee.setdefault(edge.callee_qualname, []).append(edge)

    # --- Queries ---

    def endpoint_handlers(self) -> list[str]:
        """Return qualnames of all route handler functions."""
        return [r.handler_qualname for r in self.routes]

    def all_functions(self) -> list[str]:
        """Return every known function qualname in stable order."""
        return sorted(self.g.nodes())

    def node_kind(self, qualname: str) -> str:
        """Return the recorded node kind for a function."""
        if qualname not in self.g:
            return "unknown"
        return self.g.nodes[qualname].get("kind", "function")

    def reachable_from(self, handler: str) -> set[str]:
        """Return all functions reachable from a handler (including itself)."""
        if handler not in self.g:
            return {handler}
        return nx.descendants(self.g, handler) | {handler}

    def callers_of(self, function: str) -> list[str]:
        """Return direct callers of a function."""
        if function not in self.g:
            return []
        return sorted(self.g.predecessors(function))

    def callees_of(self, function: str) -> list[str]:
        """Return direct callees of a function."""
        if function not in self.g:
            return []
        return sorted(self.g.successors(function))

    def call_edges_from(self, caller: str) -> list[CallEdge]:
        """Return call edges originating in a function."""
        return self._calls_by_caller.get(caller, [])

    def call_edges_to(self, callee: str) -> list[CallEdge]:
        """Return call edges targeting a function."""
        return self._calls_by_callee.get(callee, [])

    def call_edges_between(self, caller: str, callee: str) -> list[CallEdge]:
        """Return call-site facts for a caller -> callee pair."""
        return self._calls_by_pair.get((caller, callee), [])

    def accesses_in(self, function: str) -> list[InputAccessFact]:
        """Return input accesses directly in a function."""
        return self._accesses_by_func.get(function, [])

    def accesses_reachable_from(self, handler: str) -> list[InputAccessFact]:
        """Return all input accesses reachable from a handler."""
        result: list[InputAccessFact] = []
        for func in self.reachable_from(handler):
            result.extend(self.accesses_in(func))
        return result

    def merges_in(self, function: str) -> list[DictMergeFact]:
        """Return dict merges directly in a function."""
        return self._merges_by_func.get(function, [])

    def merges_reachable_from(self, handler: str) -> list[DictMergeFact]:
        """Return all dict merges reachable from a handler."""
        result: list[DictMergeFact] = []
        for func in self.reachable_from(handler):
            result.extend(self.merges_in(func))
        return result

    def routes_for_handler(self, handler: str) -> list[RouteFact]:
        """Return route facts for a handler function."""
        return self._routes_by_handler.get(handler, [])

    def before_requests_for(self, blueprint: str | None) -> list[BeforeRequestFact]:
        """Return before_request middleware for a blueprint."""
        return self._before_by_blueprint.get(blueprint, [])

    def node_locations(self, qualname: str) -> list:
        """Return all source locations tied directly to a function node."""
        locations = []
        locations.extend(r.location for r in self.routes_for_handler(qualname))
        locations.extend(a.location for a in self.accesses_in(qualname))
        locations.extend(m.location for m in self.merges_in(qualname))
        for b in self.before_requests:
            if b.function_qualname == qualname:
                locations.append(b.location)
        locations.extend(e.location for e in self.call_edges_from(qualname))
        seen: set[tuple[str, int, int]] = set()
        unique = []
        for loc in sorted(locations, key=lambda loc: (loc.file, loc.line, loc.col)):
            key = (loc.file, loc.line, loc.col)
            if key not in seen:
                seen.add(key)
                unique.append(loc)
        return unique

    def node_primary_location(self, qualname: str):
        """Return the best representative location for a function node."""
        locations = self.node_locations(qualname)
        return locations[0] if locations else None

    def call_path(self, source: str, target: str) -> list[str] | None:
        """Return shortest call path from source to target, or None."""
        if source not in self.g or target not in self.g:
            return None
        try:
            return nx.shortest_path(self.g, source, target)
        except nx.NetworkXNoPath:
            return None

    def handlers_reaching(self, target: str) -> list[str]:
        """Return endpoint handlers that can reach a given function."""
        handlers = set(self.endpoint_handlers())
        return sorted(
            h
            for h in handlers
            if h == target or (h in self.g and target in self.g and nx.has_path(self.g, h, target))
        )

    # --- Convenience iterators for rule authoring ---

    def by_endpoint(self) -> list[tuple[str, RouteFact, list[InputAccessFact]]]:
        """Iterate (handler_qualname, route, accesses) for each endpoint.

        This is the primary entry point for writing detection rules::

            for handler, route, accesses in graph.by_endpoint():
                sources = {a.source for a in accesses}
                ...
        """
        result = []
        for route in self.routes:
            handler = route.handler_qualname
            accesses = self.accesses_reachable_from(handler)
            result.append((handler, route, accesses))
        return result

    def endpoint_summary(self, handler: str) -> dict:
        """Return a notebook-friendly summary for an endpoint handler."""
        routes = self.routes_for_handler(handler)
        route = routes[0] if routes else None
        accesses = self.accesses_reachable_from(handler)
        merges = self.merges_reachable_from(handler)
        blueprint = route.blueprint if route else None
        middleware = self.before_requests_for(blueprint)
        reachable = sorted(self.reachable_from(handler))
        keys = sorted({a.key_literal for a in accesses if a.key_literal})
        sources = sorted({a.source.value for a in accesses})
        accessors = sorted({a.accessor.value for a in accesses})
        return {
            "handler": handler,
            "route": route,
            "routes": routes,
            "methods": sorted({m for r in routes for m in r.methods}) if routes else [],
            "rule": route.rule if route else None,
            "blueprint": blueprint,
            "reachable": reachable,
            "accesses": accesses,
            "merges": merges,
            "middleware": middleware,
            "keys": keys,
            "sources": sources,
            "accessors": accessors,
            "access_count": len(accesses),
            "merge_count": len(merges),
            "middleware_count": len(middleware),
            "fan_out": len(self.callees_of(handler)),
            "fan_in": len(self.callers_of(handler)),
            "location": route.location if route else self.node_primary_location(handler),
        }

    def endpoint_summaries(self) -> list[dict]:
        """Return summaries for every endpoint."""
        return [self.endpoint_summary(handler) for handler in self.endpoint_handlers()]

    def function_summary(self, qualname: str) -> dict:
        """Return a notebook-friendly summary for any function node."""
        accesses = self.accesses_in(qualname)
        merges = self.merges_in(qualname)
        routes = self.routes_for_handler(qualname)
        before = [b for b in self.before_requests if b.function_qualname == qualname]
        return {
            "qualname": qualname,
            "kind": self.node_kind(qualname),
            "location": self.node_primary_location(qualname),
            "locations": self.node_locations(qualname),
            "routes": routes,
            "accesses": accesses,
            "merges": merges,
            "before_requests": before,
            "callers": self.callers_of(qualname),
            "callees": self.callees_of(qualname),
            "call_edges_from": self.call_edges_from(qualname),
            "call_edges_to": self.call_edges_to(qualname),
            "keys": sorted({a.key_literal for a in accesses if a.key_literal}),
            "sources": sorted({a.source.value for a in accesses}),
        }

    def subgraph_nodes(
        self,
        *,
        endpoints: list[str] | None = None,
        targets: list[str] | None = None,
        radius: int = 1,
    ) -> set[str]:
        """Return a focused node set around endpoints/targets for UI filtering."""
        nodes: set[str] = set()
        if endpoints:
            for handler in endpoints:
                nodes.update(self.reachable_from(handler))
                nodes.add(handler)
        if targets:
            for target in targets:
                nodes.add(target)
                frontier = {target}
                for _ in range(max(radius, 0)):
                    next_frontier: set[str] = set()
                    for current in frontier:
                        next_frontier.update(self.callers_of(current))
                        next_frontier.update(self.callees_of(current))
                    frontier = next_frontier - nodes
                    nodes.update(next_frontier)
        return nodes

    def by_key(self, key: str | None = None) -> KeyAccessView:
        """Group all accesses by key literal.

        If `key` is provided, returns only accesses for that key.
        """
        from collections import defaultdict

        grouped: dict[str, list[InputAccessFact]] = defaultdict(list)
        for a in self.input_accesses:
            if a.key_literal:
                grouped[a.key_literal].append(a)
        if key is not None:
            return KeyAccessView({key: grouped.get(key, [])})
        return KeyAccessView(dict(grouped))

    def sources_for(self, handler: str) -> set:
        """Return set of InputSources used by an endpoint."""
        return {a.source for a in self.accesses_reachable_from(handler)}

    def stats(self) -> StatsView:
        """Return summary statistics about this graph."""
        return StatsView(
            {
                "nodes": self.g.number_of_nodes(),
                "edges": self.g.number_of_edges(),
                "call_sites": len(self.call_edges),
                "routes": len(self.routes),
                "input_accesses": len(self.input_accesses),
                "before_requests": len(self.before_requests),
                "dict_merges": len(self.dict_merges),
                "unique_keys": len({a.key_literal for a in self.input_accesses if a.key_literal}),
                "unique_sources": len({a.source for a in self.input_accesses}),
            }
        )

    def __repr__(self) -> str:
        s = self.stats()
        return (
            f"AnalysisGraph({s['routes']} routes, "
            f"{s['input_accesses']} accesses, "
            f"{s['nodes']} nodes, {s['edges']} edges)"
        )

    def _repr_html_(self) -> str:
        """Rich HTML rendering for Jupyter notebooks."""
        # Lazy import to avoid circular dependency (display.py imports graph.py
        # under TYPE_CHECKING).
        from ..reporting.display import graph_html

        s = self.stats()
        header = (
            f"<div style='font-family:system-ui;margin-bottom:8px'>"
            f"<b>{s['routes']}</b> routes, "
            f"<b>{s['input_accesses']}</b> accesses, "
            f"<b>{s['nodes']}</b> nodes, "
            f"<b>{s['edges']}</b> edges"
            f"</div>"
        )
        return f"<div style='font-family:system-ui'>{header}{graph_html(self)}</div>"

    def _repr_mimebundle_(self, **kwargs: object) -> dict:
        """Render the interactive workbench in notebooks when widgets are available."""
        try:
            from ..notebook.widgets import Explorer

            return Explorer(self)._repr_mimebundle_(**kwargs)
        except Exception:
            return {"text/html": self._repr_html_()}


def build_analysis_graph(
    result: ExtractionResult, target_root: str | Path | None = None
) -> AnalysisGraph:
    """Build an AnalysisGraph from backend extraction results."""
    g = nx.DiGraph()

    # Add nodes for all known functions
    for route in result.routes:
        g.add_node(route.handler_qualname, kind="endpoint")
    for access in result.input_accesses:
        g.add_node(access.function_qualname, kind="function")
    for br in result.before_requests:
        g.add_node(br.function_qualname, kind="middleware")

    # Add edges
    for edge in result.call_edges:
        g.add_node(edge.caller_qualname)
        g.add_node(edge.callee_qualname)
        if g.has_edge(edge.caller_qualname, edge.callee_qualname):
            edge_data = g.edges[edge.caller_qualname, edge.callee_qualname]
            edge_data.setdefault("callsites", []).append(edge)
            edge_data["call_count"] = len(edge_data["callsites"])
        else:
            g.add_edge(
                edge.caller_qualname,
                edge.callee_qualname,
                callsites=[edge],
                call_count=1,
            )

    return AnalysisGraph(
        g=g,
        target_root=Path(target_root).resolve() if target_root is not None else None,
        call_edges=result.call_edges,
        routes=result.routes,
        input_accesses=result.input_accesses,
        before_requests=result.before_requests,
        dict_merges=result.dict_merges,
    )
