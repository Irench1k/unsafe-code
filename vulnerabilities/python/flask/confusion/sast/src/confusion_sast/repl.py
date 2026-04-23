"""Interactive REPL helpers for IPython/Jupyter notebook exploration.

Import everything for interactive use::

    from confusion_sast.repl import *

    # Scan and get findings
    r = scan("path/to/flask/app")
    r.print(verbose=True)

    # Or extract just the graph (no rules)
    g = extract("path/to/flask/app")
    g.stats()
    g.by_endpoint()

    # Explore
    show_graph(g)
    show_source(g.input_accesses[0])

    # Run specific rules
    results = run_rule("CONF-001", g)
    show(results)

    # Write and test ad-hoc rules
    @detect("MY-001", severity="high")
    def my_check(g):
        for handler, route, accesses in g.by_endpoint():
            ...
            yield finding("problem found", evidence=accesses)

    results = run_fn(my_check, g)
    show(results)

    # Filter and query
    routes(r)
    accesses(r, source="form", key="item")
    endpoint_detail("create_new_order", r)
"""

from __future__ import annotations

from collections import defaultdict

from .analysis.graph import AnalysisGraph
from .detection.rules import run_rules
from .detection.toolkit import (
    AccessorKind,
    DictMergeFact,
    Finding,
    InputAccessFact,
    InputSource,
    RouteFact,
    Severity,
    detect,
    finding,
    run_fn,
    run_rule,
)

# Notebook helpers (import from _helpers to avoid circular import)
from .notebook._helpers import (
    BatchResult,
    Exercise,
    Section,
    TargetRegistry,
    batch_load,
    batch_run,
    compare,
    finding_paths,
    load,
    targets,
)
from .pipeline import ScanResult, extract, scan
from .reporting.display import (
    show_graph,
    show_source,
    source_context,
)
from .reporting.formatter import format_finding, format_findings
from .rich_types import AccessListView, DivergentKeysView, EndpointDetailView

__all__ = [
    # Pipeline
    "scan",
    "extract",
    # Display
    "show",
    "show_graph",
    "show_source",
    "source_context",
    # Query helpers
    "routes",
    "accesses",
    "endpoint_detail",
    "diff_keys",
    # Rule authoring
    "detect",
    "finding",
    "run_fn",
    "run_rule",
    "run_rules",
    # Types (for rule authoring)
    "InputSource",
    "AccessorKind",
    "Severity",
    "Finding",
    "InputAccessFact",
    "RouteFact",
    "DictMergeFact",
    "AnalysisGraph",
    "ScanResult",
    # Notebook helpers
    "targets",
    "load",
    "batch_load",
    "batch_run",
    "finding_paths",
    "compare",
    "TargetRegistry",
    "Section",
    "Exercise",
    "BatchResult",
]


# ---------------------------------------------------------------------------
# Generic show() — display anything nicely
# ---------------------------------------------------------------------------


def show(obj, **kwargs) -> None:
    """Display any SAST object with appropriate formatting.

    Works for: ScanResult, Finding, list[Finding], AnalysisGraph,
    InputAccessFact, RouteFact, Location.
    """
    if isinstance(obj, ScanResult):
        obj.print(verbose=kwargs.get("verbose", True))
    elif isinstance(obj, list) and obj and isinstance(obj[0], Finding):
        print(format_findings(obj, verbose=kwargs.get("verbose", True)))
    elif isinstance(obj, Finding):
        print(format_finding(obj, verbose=kwargs.get("verbose", True)))
    elif isinstance(obj, AnalysisGraph):
        show_graph(obj)
    elif hasattr(obj, "location"):
        show_source(obj, **kwargs)
    else:
        print(repr(obj))


# ---------------------------------------------------------------------------
# Data-returning query helpers
# ---------------------------------------------------------------------------


def routes(result: ScanResult | AnalysisGraph) -> list[RouteFact]:
    """Return all discovered routes."""
    if isinstance(result, ScanResult):
        return result.extraction.routes
    return result.routes


def accesses(
    result: ScanResult | AnalysisGraph,
    source: str | InputSource | None = None,
    key: str | None = None,
    handler: str | None = None,
    accessor: str | AccessorKind | None = None,
) -> AccessListView:
    """Return input accesses, with optional filtering.

    Returns a list — use show() to display, or iterate directly::

        for a in accesses(r, source="form", key="item"):
            print(a.function_qualname, a.raw_code)
    """
    if isinstance(result, ScanResult):
        items = result.extraction.input_accesses
    else:
        items = result.input_accesses

    if source is not None:
        if isinstance(source, str):
            source = InputSource(source)
        items = [a for a in items if a.source == source]

    if key is not None:
        items = [a for a in items if a.key_literal == key]

    if handler is not None:
        items = [a for a in items if handler in a.function_qualname]

    if accessor is not None:
        if isinstance(accessor, str):
            accessor = AccessorKind(accessor)
        items = [a for a in items if a.accessor == accessor]

    return AccessListView(items)


def endpoint_detail(
    handler_substr: str,
    result: ScanResult | AnalysisGraph,
) -> EndpointDetailView:
    """Return detailed access info for endpoints matching the substring.

    Returns dict[handler_qualname, {route, accesses, sources, keys, merges}].
    """
    if isinstance(result, ScanResult):
        graph = result.graph
        all_routes = result.extraction.routes
    else:
        graph = result
        all_routes = result.routes

    output: dict[str, dict] = {}
    for route in all_routes:
        h = route.handler_qualname
        if handler_substr not in h:
            continue
        ep_accesses = graph.accesses_reachable_from(h)
        ep_merges = graph.merges_reachable_from(h)
        output[h] = {
            "route": route,
            "accesses": ep_accesses,
            "sources": {a.source for a in ep_accesses},
            "keys": {a.key_literal for a in ep_accesses if a.key_literal},
            "merges": ep_merges,
        }
    return EndpointDetailView(output)


def diff_keys(result: ScanResult | AnalysisGraph) -> DivergentKeysView:
    """Find keys accessed with different sources or accessors.

    Returns dict[key, {sources, accessors, accesses}] only for keys
    that show divergence (different sources OR different accessors).
    """
    if isinstance(result, ScanResult):
        all_accesses = result.extraction.input_accesses
    else:
        all_accesses = result.input_accesses

    by_key: dict[str, list[InputAccessFact]] = defaultdict(list)
    for a in all_accesses:
        if a.key_literal:
            by_key[a.key_literal].append(a)

    divergent = {}
    for key, key_accesses in sorted(by_key.items()):
        src = {a.source for a in key_accesses}
        acc = {a.accessor for a in key_accesses}
        if len(src) > 1 or len(acc) > 1:
            divergent[key] = {
                "sources": src,
                "accessors": acc,
                "accesses": key_accesses,
            }
    return DivergentKeysView(divergent)
