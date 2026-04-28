"""Rich display for Jupyter notebooks and IPython terminal.

Provides source code snippets, HTML finding cards, and graph visualization.
Auto-detects Jupyter vs terminal and renders appropriately.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer, guess_lexer_for_filename
from pygments.util import ClassNotFound

from ..models import Finding, InputAccessFact, Location, Severity

if TYPE_CHECKING:
    from ..analysis.graph import AnalysisGraph


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------


def _in_notebook() -> bool:
    try:
        shell = get_ipython().__class__.__name__  # type: ignore[name-defined]
        return shell in ("ZMQInteractiveShell", "Shell")
    except NameError:
        return False


def _display_html(html: str) -> None:
    from IPython.display import HTML, display
    display(HTML(html))


# ---------------------------------------------------------------------------
# Source code snippets
# ---------------------------------------------------------------------------

_SOURCE_CACHE: dict[str, list[str]] = {}


def _read_source(file_path: str) -> list[str]:
    if file_path not in _SOURCE_CACHE:
        try:
            _SOURCE_CACHE[file_path] = Path(file_path).read_text().splitlines()
        except (OSError, UnicodeDecodeError):
            _SOURCE_CACHE[file_path] = []
    return _SOURCE_CACHE[file_path]


def source_context(location: Location, context: int = 3) -> str:
    """Return source lines around a location as a formatted string."""
    lines = _read_source(location.file)
    if not lines:
        return f"  (cannot read {location.file})"

    start = max(0, location.line - context - 1)
    end = min(len(lines), location.line + context)
    target_idx = location.line - 1

    result = []
    for i in range(start, end):
        marker = " >> " if i == target_idx else "    "
        result.append(f"{marker}{i + 1:4d} | {lines[i]}")
    return "\n".join(result)


def show_source(obj, context: int = 3) -> None:
    """Show source code context for a Location, InputAccessFact, or Finding."""
    if isinstance(obj, Location):
        _show_one_source(obj, context)
    elif isinstance(obj, InputAccessFact):
        _show_one_source(obj.location, context, label=obj.raw_code)
    elif isinstance(obj, Finding):
        _show_finding_sources(obj, context)
    elif hasattr(obj, "location"):
        _show_one_source(obj.location, context)
    else:
        print(f"Cannot show source for {type(obj).__name__}")


def _show_one_source(loc: Location, context: int, label: str = "") -> None:
    if _in_notebook():
        html = _source_html(loc, context, label)
        _display_html(html)
    else:
        if label:
            print(f"  {label}")
        print(f"  {loc}:")
        print(source_context(loc, context))
        print()


def _show_finding_sources(finding: Finding, context: int) -> None:
    if _in_notebook():
        _display_html(_finding_html(finding, context))
    else:
        print(f"[{finding.severity.value.upper()}] {finding.rule_id}: {finding.title}")
        print(f"  {finding.location_1}")
        if finding.location_2 is not None:
            print(f"  Related: {finding.location_2}")
        print()
        for ev in finding.evidence:
            if hasattr(ev, "location"):
                label = ev.raw_code if hasattr(ev, "raw_code") else ""
                print(f"  {label}")
                print(source_context(ev.location, context))
                print()


# ---------------------------------------------------------------------------
# HTML rendering for Jupyter
# ---------------------------------------------------------------------------

_SEVERITY_COLORS = {
    Severity.CRITICAL: "#dc2626",
    Severity.HIGH: "#ea580c",
    Severity.MEDIUM: "#ca8a04",
    Severity.LOW: "#2563eb",
    Severity.INFO: "#6b7280",
}


def _lexer_for_file(file_path: str):
    try:
        return guess_lexer_for_filename(file_path, "\n".join(_read_source(file_path)))
    except ClassNotFound:
        return PythonLexer()


def _highlight_file_html(file_path: str) -> list[str]:
    lines = _read_source(file_path)
    if not lines:
        return []
    lexer = _lexer_for_file(file_path)
    formatter = HtmlFormatter(nowrap=True)
    return highlight("\n".join(lines), lexer, formatter).splitlines()


def _source_html(loc: Location, context: int = 3, label: str = "") -> str:
    lines = _read_source(loc.file)
    highlighted = _highlight_file_html(loc.file)
    if not lines or not highlighted:
        return f"<pre style='color:#888'>(cannot read {loc.file})</pre>"

    target_idx = loc.line - 1
    parts = [
        "<div style='border:1px solid #dbe4f0;border-radius:10px;background:#111827;"
        "color:#e2e8f0;resize:vertical;overflow:auto;max-height:240px;min-height:160px'>"
    ]
    if label:
        parts.append(
            f"<div style='padding:8px 10px 0 10px;font-size:12px;color:#cbd5e1'>{_esc(label)}</div>"
        )
    parts.append(
        f"<div style='padding:4px 10px 8px 10px;font-size:11px;color:#94a3b8'>{_esc(loc.file)}:{loc.line}</div>"
    )
    parts.append("<div style='overflow:auto;max-height:180px;padding-bottom:6px'>")
    for i, html_line in enumerate(highlighted):
        classes = []
        if i == target_idx:
            classes.append("background:rgba(56,189,248,0.14);border-left:3px solid #38bdf8;")
        line_style = "".join(classes)
        parts.append(
            f"<div style='display:grid;grid-template-columns:64px minmax(0,1fr);font-family:monospace;"
            f"font-size:12px;line-height:1.55rem;{line_style}'>"
            f"<span style='text-align:right;padding-right:10px;color:#64748b;user-select:none'>{i+1}</span>"
            f"<span style='white-space:pre'>{html_line or '&nbsp;'}</span>"
            "</div>"
        )
    parts.append("</div></div>")
    parts.append(
        "<style>"
        ".k,.kn,.kp,.kr,.kc{color:#c084fc}.n,.nn,.nb,.nf,.fm{color:#e2e8f0}"
        ".s,.sa,.sb,.sc,.sd,.s1,.s2{color:#86efac}.mi,.mf,.il{color:#fbbf24}"
        ".o,.ow{color:#fda4af}.c,.c1,.cm{color:#64748b;font-style:italic}"
        ".nd,.fm{color:#7dd3fc}.na,.bp,.nc{color:#93c5fd}"
        "</style>"
    )
    return "".join(parts)


def _finding_html(finding: Finding, context: int = 3) -> str:
    color = _SEVERITY_COLORS.get(finding.severity, "#6b7280")
    sev = finding.severity.value.upper()

    parts = [
        f"<div style='border:1px solid {color};border-radius:8px;padding:12px;margin:8px 0;font-family:system-ui'>",
        f"  <div style='margin-bottom:8px'>",
        f"    <span style='background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold'>{sev}</span>",
        f"    <span style='font-weight:bold;margin-left:8px'>{finding.rule_id}</span>",
        f"    <span style='margin-left:4px'>{_esc(finding.title)}</span>",
        f"  </div>",
    ]

    if finding.endpoint:
        methods = ", ".join(finding.endpoint.methods)
        parts.append(f"  <div style='font-size:13px;color:#666;margin-bottom:8px'>Endpoint: {methods} {finding.endpoint.rule or '?'}</div>")

    if finding.description and finding.description != finding.title:
        parts.append(f"  <div style='font-size:13px;margin-bottom:8px'>{_esc(finding.description)}</div>")

    if finding.evidence:
        parts.append("  <details><summary style='cursor:pointer;font-size:13px;color:#666'>Evidence ({} items)</summary>".format(len(finding.evidence)))
        for ev in finding.evidence:
            if hasattr(ev, "location"):
                parts.append(_source_html(ev.location, context, ev.raw_code if hasattr(ev, "raw_code") else ""))
        parts.append("  </details>")

    parts.append("</div>")
    return "\n".join(parts)


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Graph HTML for Jupyter
# ---------------------------------------------------------------------------


def graph_html(graph: AnalysisGraph) -> str:
    """Render a graph summary as an HTML table."""
    rows = []
    for handler, route, accesses in graph.by_endpoint():
        if not accesses:
            continue
        methods = ", ".join(route.methods)
        sources = {a.source.value for a in accesses}
        keys = {a.key_literal for a in accesses if a.key_literal}

        flags = []
        if len(sources) > 1:
            flags.append(f"<span style='color:#ea580c'>MULTI-SOURCE</span>")
        if any(k + "s" in keys for k in keys if not k.endswith("s")):
            flags.append(f"<span style='color:#dc2626'>SINGULAR/PLURAL</span>")

        rows.append(
            f"<tr>"
            f"<td style='font-family:monospace;font-size:13px;text-align:left;padding:4px 8px'>{methods}</td>"
            f"<td style='font-family:monospace;font-size:13px;text-align:left;padding:4px 8px'>{route.rule or '?'}</td>"
            f"<td style='font-size:12px;text-align:left;padding:4px 8px'>{', '.join(sorted(sources))}</td>"
            f"<td style='font-size:12px;text-align:left;padding:4px 8px'>{', '.join(sorted(keys))}</td>"
            f"<td style='text-align:left;padding:4px 8px'>{' '.join(flags)}</td>"
            f"</tr>"
        )

    return (
        "<table style='border-collapse:collapse;width:100%'>"
        "<tr style='background:#f1f5f9'>"
        "<th style='text-align:left;padding:4px 8px'>Methods</th>"
        "<th style='text-align:left;padding:4px 8px'>Rule</th>"
        "<th style='text-align:left;padding:4px 8px'>Sources</th>"
        "<th style='text-align:left;padding:4px 8px'>Keys</th>"
        "<th style='text-align:left;padding:4px 8px'>Flags</th>"
        "</tr>"
        + "\n".join(rows)
        + "</table>"
    )


def show_graph(graph: AnalysisGraph) -> None:
    """Display a graph summary. HTML in Jupyter, text in terminal."""
    if _in_notebook():
        stats = graph.stats()
        header = (
            f"<div style='font-family:system-ui;margin-bottom:8px'>"
            f"<b>{stats['routes']}</b> routes, "
            f"<b>{stats['input_accesses']}</b> accesses, "
            f"<b>{stats['nodes']}</b> nodes, "
            f"<b>{stats['edges']}</b> edges"
            f"</div>"
        )
        _display_html(header + graph_html(graph))
    else:
        print(repr(graph))
        print()
        for handler, route, accesses in graph.by_endpoint():
            if not accesses:
                continue
            methods = ", ".join(route.methods)
            sources = {a.source.value for a in accesses}
            keys = {a.key_literal for a in accesses if a.key_literal}
            print(f"  {methods:10s} {route.rule or '?':25s} sources={','.join(sorted(sources)):15s} keys={','.join(sorted(keys))}")
