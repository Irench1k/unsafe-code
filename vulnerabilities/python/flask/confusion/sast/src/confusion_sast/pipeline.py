"""High-level pipeline for scanning and interactive exploration.

This module provides the main entry point for both CLI and notebook usage.
It wires together backend → graph → detection → reporting.
"""

from __future__ import annotations

from pathlib import Path

from .analysis.graph import AnalysisGraph, build_analysis_graph
from .backends.ast_backend import ASTBackend
from .backends.interface import Backend, ExtractionResult
from .detection.rules import get_all_rules, run_rules
from .models import Finding, InputSource
from .reporting.formatter import format_findings


def extract(
    target: str | Path,
    backend: str | Backend = "ast",
) -> AnalysisGraph:
    """Extract facts from source code and return a queryable graph.

    Use this for interactive exploration when you don't need findings yet::

        g = extract("path/to/flask/app")
        g.stats()
        g.by_endpoint()
    """
    if isinstance(backend, str):
        backend = _get_backend(backend)
    target = Path(target).resolve()
    result = backend.extract(target)
    return build_analysis_graph(result, target_root=target)


def scan(
    target: str | Path,
    backend: str | Backend = "ast",
    rules: list[str] | None = None,
    verbose: bool = False,
) -> ScanResult:
    """Run a full scan and return structured results.

    Usage::

        result = scan("/path/to/flask/app")
        result.print()           # formatted report
        result.findings          # list of Finding objects
        result.graph             # AnalysisGraph for further exploration
    """
    if isinstance(backend, str):
        backend = _get_backend(backend)

    target = Path(target).resolve()
    extraction = backend.extract(target)
    graph = build_analysis_graph(extraction, target_root=target)
    findings = run_rules(graph, rules)

    return ScanResult(
        target=target,
        extraction=extraction,
        graph=graph,
        findings=findings,
        verbose=verbose,
    )


def _get_backend(name: str) -> Backend:
    if name == "ast":
        return ASTBackend()
    elif name == "joern":
        from .backends.joern_backend import JoernBackend
        return JoernBackend()
    elif name == "codeql":
        from .backends.codeql_backend import CodeQLBackend
        return CodeQLBackend()
    elif name == "chimera":
        from .backends.chimera_backend import ChimeraBackend
        return ChimeraBackend()
    raise ValueError(f"Unknown backend: {name!r}. Available: ast, joern, codeql, chimera")


class ScanResult:
    """Result of a scan, with convenience methods for exploration."""

    def __init__(
        self,
        target: Path,
        extraction: ExtractionResult,
        graph: AnalysisGraph,
        findings: list[Finding],
        verbose: bool = False,
    ) -> None:
        self.target = target
        self.extraction = extraction
        self.graph = graph
        self.findings = findings
        self.verbose = verbose

    def print(self, verbose: bool | None = None) -> None:
        v = verbose if verbose is not None else self.verbose
        print(format_findings(self.findings, verbose=v))

    def summary(self) -> dict:
        from collections import Counter
        return {
            "files_analyzed": len(self.extraction.files_analyzed),
            "routes": len(self.extraction.routes),
            "input_accesses": len(self.extraction.input_accesses),
            "call_edges": len(self.extraction.call_edges),
            "findings": len(self.findings),
            "by_severity": dict(Counter(f.severity.value for f in self.findings)),
            "by_rule": dict(Counter(f.rule_id for f in self.findings)),
        }

    def routes(self) -> list:
        return self.extraction.routes

    def accesses(self, source: InputSource | str | None = None) -> list:
        accesses = self.extraction.input_accesses
        if source is not None:
            if isinstance(source, str):
                source = InputSource(source)
            accesses = [a for a in accesses if a.source == source]
        return accesses

    def endpoint_accesses(self, handler: str | None = None) -> dict:
        """Return accesses grouped by endpoint handler."""
        result = {}
        for route in self.extraction.routes:
            h = route.handler_qualname
            if handler and handler not in h:
                continue
            result[h] = self.graph.accesses_reachable_from(h)
        return result

    def __repr__(self) -> str:
        s = self.summary()
        return (
            f"ScanResult({self.target.name}: "
            f"{s['routes']} routes, "
            f"{s['input_accesses']} accesses, "
            f"{s['findings']} findings)"
        )

    def _repr_html_(self) -> str:
        """Rich HTML rendering for Jupyter notebooks."""
        from .reporting.display import _finding_html
        s = self.summary()
        parts = [
            f"<div style='font-family:system-ui'>",
            f"<h3>ScanResult: {self.target.name}</h3>",
            f"<div style='margin-bottom:12px'>",
            f"  <b>{s['routes']}</b> routes, "
            f"  <b>{s['input_accesses']}</b> accesses, "
            f"  <b>{s['findings']}</b> findings",
            f"</div>",
        ]
        if self.findings:
            parts.append(f"<h4>Findings ({len(self.findings)})</h4>")
            for f in self.findings:
                parts.append(_finding_html(f))
        parts.append("</div>")
        return "\n".join(parts)
