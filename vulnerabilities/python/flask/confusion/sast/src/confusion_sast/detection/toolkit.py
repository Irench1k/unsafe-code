"""Rule authoring toolkit for interactive exploration and prototyping.

Provides ergonomic helpers that reduce Finding boilerplate and make it
easy to write, test, and iterate on detection rules in IPython/Jupyter.

Usage in IPython::

    from confusion_sast.detection.toolkit import *

    g = extract("path/to/app")

    # Quick ad-hoc rule
    @detect("MY-001", severity="high")
    def my_rule(g):
        for handler, route, accesses in g.by_endpoint():
            args = [a for a in accesses if a.source == InputSource.ARGS]
            form = [a for a in accesses if a.source == InputSource.FORM]
            if args and form:
                yield finding(
                    "Same endpoint uses both args and form",
                    evidence=args + form,
                    endpoint=route,
                )

    # Run it
    results = run_fn(my_rule, g)
    show(results)
"""

from __future__ import annotations

from typing import Callable, Generator

from ..analysis.graph import AnalysisGraph
from ..models import (
    AccessorKind,
    DictMergeFact,
    Finding,
    InputAccessFact,
    InputSource,
    Location,
    RouteFact,
    Severity,
)
from .rules import _RULES, run_rules


# Re-export commonly needed types for star imports
__all__ = [
    "InputSource",
    "AccessorKind",
    "Severity",
    "Finding",
    "InputAccessFact",
    "RouteFact",
    "DictMergeFact",
    "finding",
    "detect",
    "run_fn",
    "run_rule",
    "run_rules",
]


# ---------------------------------------------------------------------------
# Finding builder — reduce boilerplate
# ---------------------------------------------------------------------------

_SEVERITY_MAP = {
    "info": Severity.INFO,
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "med": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
    "crit": Severity.CRITICAL,
}


def finding(
    title: str,
    evidence: list | None = None,
    *,
    rule_id: str = "ADHOC",
    severity: str | Severity = "medium",
    description: str = "",
    endpoint: RouteFact | None = None,
    location: Location | None = None,
    details: dict | None = None,
) -> Finding:
    """Create a Finding with minimal boilerplate.

    The location is auto-inferred from the first evidence item if not provided.
    The description defaults to the title if not provided.

    Usage::

        finding("Key 'item' from both args and form", [access1, access2], severity="high")
    """
    evidence = evidence or []

    if isinstance(severity, str):
        severity = _SEVERITY_MAP.get(severity.lower(), Severity.MEDIUM)

    if location is None and evidence:
        first = evidence[0]
        if hasattr(first, "location"):
            location = first.location
    if location is None:
        location = Location("", 0)

    return Finding(
        rule_id=rule_id,
        title=title,
        description=description or title,
        severity=severity,
        location_1=location,
        evidence=evidence,
        endpoint=endpoint,
        details=details or {},
    )


# ---------------------------------------------------------------------------
# @detect decorator — lightweight rule definition for prototyping
# ---------------------------------------------------------------------------


def detect(rule_id: str, *, severity: str | Severity = "medium", register: bool = False):
    """Decorator for lightweight rule functions that yield findings.

    The decorated function receives an AnalysisGraph and should yield
    Finding objects (use the `finding()` builder).

    If `register=True`, the rule is added to the global registry so it
    runs with `run_all_rules()` and the CLI.

    Usage::

        @detect("MY-001", severity="high")
        def my_check(g):
            for handler, route, accesses in g.by_endpoint():
                if ...:
                    yield finding("problem", accesses)
    """
    def decorator(fn: Callable[[AnalysisGraph], Generator]):
        sev = _SEVERITY_MAP.get(severity, severity) if isinstance(severity, str) else severity

        def wrapper(graph: AnalysisGraph) -> list[Finding]:
            results = []
            for f in fn(graph):
                if f.rule_id == "ADHOC":
                    f = Finding(
                        rule_id=rule_id,
                        title=f.title,
                        description=f.description,
                        severity=sev if f.severity == Severity.MEDIUM else f.severity,
                        location_1=f.location_1,
                        location_2=f.location_2,
                        evidence=f.evidence,
                        endpoint=f.endpoint,
                        details=f.details,
                    )
                results.append(f)
            return results

        wrapper.rule_id = rule_id
        wrapper.__doc__ = fn.__doc__
        wrapper.__name__ = fn.__name__
        wrapper._original = fn

        if register:
            _RULES[rule_id] = wrapper

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Rule runners for REPL
# ---------------------------------------------------------------------------


def run_fn(
    fn: Callable[[AnalysisGraph], list[Finding]] | Callable[[AnalysisGraph], Generator],
    graph: AnalysisGraph,
) -> list[Finding]:
    """Run a rule function against a graph and return findings.

    Handles both list-returning and generator-yielding functions::

        results = run_fn(my_rule, graph)
    """
    result = fn(graph)
    if hasattr(result, "__next__"):
        return list(result)
    return list(result)


def run_rule(rule_id: str, graph: AnalysisGraph) -> list[Finding]:
    """Run a registered rule by ID against a graph."""
    return run_rules(graph, [rule_id])
