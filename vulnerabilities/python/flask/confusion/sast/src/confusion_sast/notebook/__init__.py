"""Notebook-oriented API for confusion SAST.

Import everything for interactive use::

    from confusion_sast.notebook import *

    t = targets()
    g = load(t.r01.e01)
    show(g)
"""

from __future__ import annotations

import pprint

# New notebook helpers (target registry, caching, etc.)
from ._helpers import (  # noqa: F401
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

# Import from the same underlying modules that repl.py uses, avoiding
# a circular import (repl.py imports from notebook._helpers).
from ..analysis.graph import AnalysisGraph  # noqa: F401
from ..detection.rules import run_rules  # noqa: F401
from ..detection.toolkit import (  # noqa: F401
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
from ..pipeline import ScanResult, extract, scan  # noqa: F401
from ..reporting.display import show_graph, show_source, source_context  # noqa: F401

# Interactive widgets (optional — available when ipywidgets is installed)
try:
    from .widgets import (  # noqa: F401
        BatchExplorer,
        CodePathView,
        CodeViewer,
        DetailsPane,
        EndpointTable,
        EvidenceTable,
        Explorer,
        FindingsTable,
        GraphView,
    )
except ImportError:
    pass

# Import show, routes, accesses, etc. lazily after repl is fully loaded.
# These are defined in repl.py and we can't import them at module load
# time without creating a cycle. Use a deferred approach.
import importlib as _importlib


def _configure_notebook_display() -> None:
    """Install small notebook display tweaks on import.

    We keep this intentionally conservative: targeted wrapper classes provide
    the richer HTML tables, while this fallback only makes plain dict/list
    outputs less noisy in raw notebook text representations.
    """
    try:
        ip = get_ipython()  # type: ignore[name-defined]
    except NameError:
        return
    if ip is None:
        return
    try:
        plain = ip.display_formatter.formatters["text/plain"]
        plain.for_type(dict, lambda obj, _p, _cycle: _p.text(pprint.pformat(obj, width=100, sort_dicts=False)))
        plain.for_type(list, lambda obj, _p, _cycle: _p.text(pprint.pformat(obj, width=100)))
    except Exception:
        pass


_configure_notebook_display()


def __getattr__(name: str):  # noqa: N807
    """Lazily import names from repl to avoid circular import."""
    _repl_names = {"show", "routes", "accesses", "endpoint_detail", "diff_keys"}
    if name in _repl_names:
        _repl = _importlib.import_module("confusion_sast.repl")
        val = getattr(_repl, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # --- Notebook helpers ---
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
    # --- Pipeline ---
    "scan",
    "extract",
    # --- Display ---
    "show",
    "show_graph",
    "show_source",
    "source_context",
    # --- Query helpers ---
    "routes",
    "accesses",
    "endpoint_detail",
    "diff_keys",
    # --- Rule authoring ---
    "detect",
    "finding",
    "run_fn",
    "run_rule",
    "run_rules",
    # --- Types ---
    "InputSource",
    "AccessorKind",
    "Severity",
    "Finding",
    "InputAccessFact",
    "RouteFact",
    "DictMergeFact",
    "AnalysisGraph",
    "ScanResult",
    # --- Widgets ---
    "CodeViewer",
    "BatchExplorer",
    "CodePathView",
    "DetailsPane",
    "EndpointTable",
    "EvidenceTable",
    "GraphView",
    "FindingsTable",
    "Explorer",
]
