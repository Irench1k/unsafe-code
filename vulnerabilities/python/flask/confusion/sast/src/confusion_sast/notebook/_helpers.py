"""Core notebook helpers: target registry, caching, and convenience functions.

This module contains all implementations. notebook/__init__.py and repl.py
import from here (not from each other) to avoid circular imports.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

from ..analysis.graph import AnalysisGraph
from ..compare import ComparisonResult, compare_backends
from ..models import Finding
from ..pipeline import extract

__all__ = [
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
# Webapp discovery
# ---------------------------------------------------------------------------

# _helpers.py -> notebook/ -> confusion_sast/ -> src/ -> sast/
_SAST_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_WEBAPP_DEFAULT = _SAST_ROOT.parent / "webapp"


# ---------------------------------------------------------------------------
# Exercise / Section / TargetRegistry
# ---------------------------------------------------------------------------


class Exercise:
    """A single exercise directory within a section."""

    __slots__ = ("name", "short", "path", "section")

    def __init__(self, name: str, path: Path, section: str) -> None:
        self.name = name
        self.short = name.split("_", 1)[0]  # e.g. "e01"
        self.path = path
        self.section = section

    def __repr__(self) -> str:
        return f"Exercise({self.section}/{self.short}: {self.path})"

    def __fspath__(self) -> str:
        return str(self.path)

    def __str__(self) -> str:
        return f"Exercise({self.section}/{self.short}: {self.name})"


class Section:
    """A section directory (rNN_*) containing exercises."""

    __slots__ = ("name", "short", "path", "exercises")

    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.short = name.split("_", 1)[0]  # e.g. "r01"
        self.path = path
        self.exercises: dict[str, Exercise] = {}
        self._discover()

    def _discover(self) -> None:
        if not self.path.is_dir():
            return
        for child in sorted(self.path.iterdir()):
            if child.is_dir() and child.name.startswith("e"):
                ex = Exercise(child.name, child, self.short)
                self.exercises[ex.short] = ex

    def __getattr__(self, name: str) -> Exercise:
        try:
            return self.exercises[name]
        except KeyError:
            raise AttributeError(
                f"Section {self.short!r} has no exercise {name!r}. "
                f"Available: {', '.join(sorted(self.exercises))}"
            ) from None

    def __iter__(self) -> Iterator[Exercise]:
        return iter(self.exercises.values())

    def __fspath__(self) -> str:
        return str(self.path)

    def __len__(self) -> int:
        return len(self.exercises)

    def __repr__(self) -> str:
        ex_list = ", ".join(sorted(self.exercises))
        return f"Section({self.short}: {len(self.exercises)} exercises [{ex_list}])"


class TargetRegistry:
    """Auto-discovered registry of webapp sections and exercises.

    Provides attribute access::

        t = targets()
        t.r01.e01          # Path to exercise
        list(t.r01)         # all exercises in r01
        list(t)             # all sections
    """

    __slots__ = ("_root", "_sections")

    def __init__(self, webapp_dir: Path) -> None:
        self._root = webapp_dir
        self._sections: dict[str, Section] = {}
        self._discover()

    def _discover(self) -> None:
        if not self._root.is_dir():
            return
        for child in sorted(self._root.iterdir()):
            if child.is_dir() and child.name.startswith("r"):
                sec = Section(child.name, child)
                self._sections[sec.short] = sec

    def __getattr__(self, name: str) -> Section:
        try:
            return self._sections[name]
        except KeyError:
            raise AttributeError(
                f"No section {name!r}. "
                f"Available: {', '.join(sorted(self._sections))}"
            ) from None

    def __iter__(self) -> Iterator[Section]:
        return iter(self._sections.values())

    @property
    def path(self) -> Path:
        return self._root

    def __fspath__(self) -> str:
        return str(self._root)

    def __len__(self) -> int:
        return len(self._sections)

    def __repr__(self) -> str:
        lines = [f"TargetRegistry({self._root})"]
        for sec in self._sections.values():
            lines.append(f"  {sec.short}: {sec.name}")
            for ex in sec:
                lines.append(f"    {ex.short}: {ex.name}")
        return "\n".join(lines)

    def _repr_html_(self) -> str:
        rows = []
        for sec in self._sections.values():
            for i, ex in enumerate(sec):
                sec_cell = (
                    f"<td rowspan='{len(sec)}' style='vertical-align:top;padding:4px 8px;"
                    f"font-weight:bold;border-bottom:1px solid #e2e8f0;text-align:left'>{sec.short}</td>"
                    if i == 0
                    else ""
                )
                desc = ex.name.split("_", 1)[1] if "_" in ex.name else ex.name
                rows.append(
                    f"<tr>"
                    f"{sec_cell}"
                    f"<td style='padding:4px 8px;font-family:monospace;font-size:13px;text-align:left'>{ex.short}</td>"
                    f"<td style='padding:4px 8px;font-size:13px;text-align:left'>{desc}</td>"
                    f"</tr>"
                )
        return (
            "<div style='font-family:system-ui'>"
            "<h4 style='margin-bottom:8px'>Target Registry</h4>"
            "<table style='border-collapse:collapse;width:100%'>"
            "<tr style='background:#f1f5f9'>"
            "<th style='text-align:left;padding:4px 8px'>Section</th>"
            "<th style='text-align:left;padding:4px 8px'>Exercise</th>"
            "<th style='text-align:left;padding:4px 8px'>Description</th>"
            "</tr>"
            + "\n".join(rows)
            + "</table></div>"
        )


# ---------------------------------------------------------------------------
# targets() factory
# ---------------------------------------------------------------------------


def targets(webapp_dir: str | Path | None = None) -> TargetRegistry:
    """Auto-discover webapp exercises and return a target registry.

    If *webapp_dir* is not given, looks for ``webapp/`` relative to the
    SAST source tree (``sast/../webapp``).
    """
    if webapp_dir is not None:
        return TargetRegistry(Path(webapp_dir).resolve())
    return TargetRegistry(_WEBAPP_DEFAULT)


# ---------------------------------------------------------------------------
# Caching extract
# ---------------------------------------------------------------------------

_graph_cache: dict[tuple[str, str], AnalysisGraph] = {}


def load(target: str | Path | Exercise, backend: str = "ast", force: bool = False) -> AnalysisGraph:
    """Extract and cache an AnalysisGraph. Reuse on repeated calls.

    Usage::

        g = load(t.r01.e01)             # first call: runs backend
        g = load(t.r01.e01)             # subsequent: returns cached
        g = load(t.r01.e01, force=True)  # force re-extract
    """
    resolved = str(Path(os.fspath(target)).resolve())
    key = (resolved, backend)

    if not force and key in _graph_cache:
        return _graph_cache[key]

    graph = extract(resolved, backend)
    _graph_cache[key] = graph
    return graph


# ---------------------------------------------------------------------------
# Finding call paths
# ---------------------------------------------------------------------------


def finding_paths(finding: Finding, graph: AnalysisGraph) -> list[list[str] | None]:
    """For each evidence item in a finding, return the call path from the endpoint handler.

    Uses ``graph.call_path(handler_qualname, evidence_func_qualname)``.
    Returns a list parallel to ``finding.evidence``, where each entry
    is either a list of function qualnames or ``None`` if no path exists.
    """
    if finding.endpoint is None:
        return [None for _ in finding.evidence]

    handler = finding.endpoint.handler_qualname
    result: list[list[str] | None] = []

    for ev in finding.evidence:
        # RouteFact uses handler_qualname; others use function_qualname
        target_fn = getattr(ev, "function_qualname", None) or getattr(ev, "handler_qualname", None)
        if target_fn is None:
            result.append(None)
            continue
        path = graph.call_path(handler, target_fn)
        result.append(path)

    return result


# ---------------------------------------------------------------------------
# Comparison helper
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Batch operations for rule development
# ---------------------------------------------------------------------------


def batch_load(
    targets: Section | TargetRegistry | list[Exercise | str | Path],
    backend: str = "ast",
    force: bool = False,
) -> dict[str, AnalysisGraph]:
    """Load graphs for multiple exercises at once.

    Accepts a Section, a TargetRegistry, or a list of targets.
    Returns a dict keyed by exercise short name (e.g. ``"e01"``).

    Usage::

        graphs = batch_load(t.r01)
        graphs = batch_load([t.r01.e01, t.r04.e03])
        graphs = batch_load(t)  # all exercises across all sections
    """
    items: list[tuple[str, str | Path]] = []

    if isinstance(targets, Section):
        for ex in targets:
            items.append((f"{targets.short}/{ex.short}", ex))
    elif isinstance(targets, TargetRegistry):
        for sec in targets:
            for ex in sec:
                items.append((f"{sec.short}/{ex.short}", ex))
    elif isinstance(targets, list):
        for item in targets:
            if isinstance(item, Exercise):
                items.append((f"{item.section}/{item.short}", item))
            else:
                p = Path(os.fspath(item))
                items.append((p.name, item))
    else:
        raise TypeError(f"Expected Section, TargetRegistry, or list; got {type(targets).__name__}")

    result: dict[str, AnalysisGraph] = {}
    for key, target in items:
        try:
            result[key] = load(target, backend=backend, force=force)
        except Exception as exc:
            import sys
            print(f"  [{key}] FAILED: {exc}", file=sys.stderr)
    return result


class BatchResult:
    """Results of running a rule or scan across multiple exercises.

    Provides tabular summary and per-exercise detail::

        results = batch_run(my_rule, graphs)
        results              # table in Jupyter
        results.summary      # {name: count}
        results["r01/e01"]   # list[Finding] for that exercise
    """

    def __init__(self, findings: dict[str, list[Finding]]) -> None:
        self._findings = findings

    @property
    def summary(self) -> dict[str, int]:
        return {k: len(v) for k, v in self._findings.items()}

    @property
    def total(self) -> int:
        return sum(len(v) for v in self._findings.values())

    @property
    def hits(self) -> dict[str, list[Finding]]:
        """Return only exercises that produced findings."""
        return {k: v for k, v in self._findings.items() if v}

    @property
    def all_findings(self) -> list[Finding]:
        """Flatten all findings into a single list."""
        result = []
        for v in self._findings.values():
            result.extend(v)
        return result

    def __getitem__(self, key: str) -> list[Finding]:
        return self._findings[key]

    def __contains__(self, key: str) -> bool:
        return key in self._findings

    def __len__(self) -> int:
        return len(self._findings)

    def __iter__(self):
        return iter(self._findings)

    def __repr__(self) -> str:
        hit_count = sum(1 for v in self._findings.values() if v)
        return (
            f"BatchResult({len(self._findings)} exercises, "
            f"{hit_count} with findings, {self.total} total findings)"
        )

    def _repr_html_(self) -> str:
        rows = []
        for name, findings in sorted(self._findings.items()):
            count = len(findings)
            if count > 0:
                rules = ", ".join(sorted({f.rule_id for f in findings}))
                sevs = ", ".join(sorted({f.severity.value.upper() for f in findings}))
                color = "#a6e3a1" if count == 0 else "#fab387"
                rows.append(
                    f"<tr>"
                    f"<td style='padding:4px 8px;font-family:monospace'>{name}</td>"
                    f"<td style='padding:4px 8px;text-align:center;color:{color};font-weight:bold'>{count}</td>"
                    f"<td style='padding:4px 8px;font-size:12px'>{rules}</td>"
                    f"<td style='padding:4px 8px;font-size:12px'>{sevs}</td>"
                    f"</tr>"
                )
            else:
                rows.append(
                    f"<tr>"
                    f"<td style='padding:4px 8px;font-family:monospace'>{name}</td>"
                    f"<td style='padding:4px 8px;text-align:center;color:#a6e3a1'>0</td>"
                    f"<td style='padding:4px 8px;font-size:12px;color:#6c7086'>--</td>"
                    f"<td style='padding:4px 8px;font-size:12px;color:#6c7086'>--</td>"
                    f"</tr>"
                )
        return (
            "<div style='font-family:system-ui'>"
            f"<div style='margin-bottom:8px'><b>{self.total}</b> findings across "
            f"<b>{len(self._findings)}</b> exercises</div>"
            "<table style='border-collapse:collapse;width:100%'>"
            "<tr style='background:#f1f5f9'>"
            "<th style='text-align:left;padding:4px 8px'>Exercise</th>"
            "<th style='text-align:center;padding:4px 8px'>Findings</th>"
            "<th style='text-align:left;padding:4px 8px'>Rules</th>"
            "<th style='text-align:left;padding:4px 8px'>Severity</th>"
            "</tr>"
            + "\n".join(rows)
            + "</table></div>"
        )


def batch_run(
    rule_fn,
    graphs: dict[str, AnalysisGraph],
) -> BatchResult:
    """Run a rule function against multiple graphs and return a BatchResult.

    Usage::

        @detect("MY-001", severity="high")
        def my_rule(g):
            ...

        graphs = batch_load(t.r01)
        results = batch_run(my_rule, graphs)
        results  # shows summary table
    """
    from ..detection.toolkit import run_fn as _run_fn

    findings: dict[str, list[Finding]] = {}
    for name, graph in sorted(graphs.items()):
        try:
            findings[name] = _run_fn(rule_fn, graph)
        except Exception as exc:
            import sys
            print(f"  [{name}] FAILED: {exc}", file=sys.stderr)
            findings[name] = []
    return BatchResult(findings)


def compare(target: str | Path | Exercise, backends: list[str] | None = None) -> ComparisonResult:
    """Compare backends on a target, with sensible defaults.

    Wraps :func:`~confusion_sast.compare.compare_backends`.
    """
    resolved = str(Path(os.fspath(target)).resolve())
    return compare_backends(resolved, backends)
