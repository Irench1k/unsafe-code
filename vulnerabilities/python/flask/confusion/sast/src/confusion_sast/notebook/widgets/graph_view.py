"""Focused graph navigator for confusion SAST notebook workflows."""

from __future__ import annotations

from collections import OrderedDict
from typing import Callable

import ipycytoscape
import ipywidgets
import networkx as nx

from ._common import evidence_qualname, short_name

_COLORS = {
    "endpoint": "#86efac",
    "middleware": "#fde68a",
    "function": "#e2e8f0",
    "access": "#bfdbfe",
    "merge": "#fecaca",
    "highlight": "#38bdf8",
    "edge": "#94a3b8",
    "edge_highlight": "#0284c7",
    "text": "#0f172a",
    "border": "#cbd5e1",
}

_STYLE = [
    {
        "selector": "node",
        "css": {
            "background-color": _COLORS["function"],
            "label": "data(label)",
            "color": _COLORS["text"],
            "font-size": "11px",
            "font-family": "system-ui, sans-serif",
            "text-wrap": "wrap",
            "text-max-width": "140px",
            "text-valign": "center",
            "text-halign": "center",
            "shape": "roundrectangle",
            "padding": "10px",
            "width": "label",
            "height": "label",
            "border-width": "1px",
            "border-color": _COLORS["border"],
        },
    },
    {
        "selector": "node[kind = 'endpoint']",
        "css": {
            "background-color": _COLORS["endpoint"],
            "border-width": "2px",
            "font-weight": "700",
        },
    },
    {
        "selector": "node[kind = 'middleware']",
        "css": {
            "background-color": _COLORS["middleware"],
            "shape": "diamond",
            "border-width": "2px",
        },
    },
    {
        "selector": "node[has_access = 1]",
        "css": {
            "border-color": "#3b82f6",
        },
    },
    {
        "selector": "node[has_merge = 1]",
        "css": {
            "border-color": "#ef4444",
        },
    },
    {
        "selector": "node.highlighted",
        "css": {
            "background-color": _COLORS["highlight"],
            "border-color": "#0369a1",
            "color": "#082f49",
        },
    },
    {
        "selector": "node.selected",
        "css": {
            "border-width": "3px",
            "border-color": "#0f172a",
        },
    },
    {
        "selector": "edge",
        "style": {
            "width": 2,
            "line-color": _COLORS["edge"],
            "target-arrow-color": _COLORS["edge"],
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 0.9,
        },
    },
    {
        "selector": "edge.highlighted",
        "style": {
            "line-color": _COLORS["edge_highlight"],
            "target-arrow-color": _COLORS["edge_highlight"],
            "width": 4,
        },
    },
    {
        "selector": "edge.selected",
        "style": {
            "line-color": "#0f172a",
            "target-arrow-color": "#0f172a",
            "width": 4,
        },
    },
]


class GraphView:
    """Interactive graph navigator with filtering, focus scopes, and selection."""

    def __init__(self, graph, layout: str = "dagre") -> None:
        self._graph = graph
        self._layout_name = layout
        self._callbacks: list[Callable[[str], None]] = []
        self._edge_callbacks: list[Callable] = []
        self._highlighted_nodes: set[str] = set()
        self._highlighted_edges: set[tuple[str, str]] = set()
        self._selected_node: str | None = None
        self._selected_edge = None
        self._focus_nodes: set[str] | None = None

        self._scope = ipywidgets.Dropdown(
            options=[
                ("All functions", "all"),
                ("Endpoints only", "endpoints"),
                ("Focused subgraph", "focused"),
            ],
            value="all",
            layout=ipywidgets.Layout(width="180px"),
        )
        self._search = ipywidgets.Text(
            placeholder="Search by function, route, key, or source",
            layout=ipywidgets.Layout(width="100%"),
        )
        self._layout_picker = ipywidgets.Dropdown(
            options=["dagre", "breadthfirst", "cose", "circle", "concentric"],
            value=layout,
            layout=ipywidgets.Layout(width="170px"),
        )
        self._summary = ipywidgets.HTML()
        self._selection = ipywidgets.HTML()
        self._cyto_box = ipywidgets.Box(layout=ipywidgets.Layout(width="100%"))
        self._zoom_in = ipywidgets.Button(description="+", layout=ipywidgets.Layout(width="42px"))
        self._zoom_out = ipywidgets.Button(description="-", layout=ipywidgets.Layout(width="42px"))
        self._reset_view = ipywidgets.Button(description="Reset", layout=ipywidgets.Layout(width="72px"))

        toolbar = ipywidgets.HBox(
            [self._search, self._scope, self._layout_picker, self._zoom_out, self._zoom_in, self._reset_view],
            layout=ipywidgets.Layout(width="100%"),
        )
        self._container = ipywidgets.VBox(
            [self._summary, toolbar, self._cyto_box, self._selection],
            layout=ipywidgets.Layout(width="100%"),
        )

        self._search.observe(self._refresh_graph, names="value")
        self._scope.observe(self._refresh_graph, names="value")
        self._layout_picker.observe(self._refresh_graph, names="value")
        self._zoom_in.on_click(lambda _: self._adjust_zoom(1.2))
        self._zoom_out.on_click(lambda _: self._adjust_zoom(1 / 1.2))
        self._reset_view.on_click(lambda _: self._refresh_graph())

        self._refresh_graph()

    def _node_label(self, qualname: str) -> str:
        summary = self._graph.function_summary(qualname)
        parts = [short_name(qualname)]
        if summary["accesses"]:
            parts.append(f"{len(summary['accesses'])} access")
        elif summary["merges"]:
            parts.append(f"{len(summary['merges'])} merge")
        elif summary["routes"]:
            parts.append("endpoint")
        return "\n".join(parts)

    def _candidate_nodes(self) -> set[str]:
        scope = self._scope.value
        if scope == "endpoints":
            return set(self._graph.endpoint_handlers())
        if scope == "focused" and self._focus_nodes:
            return set(self._focus_nodes)
        return set(self._graph.all_functions())

    def _match_nodes(self, candidates: set[str], query: str) -> set[str]:
        if not query:
            return candidates
        needle = query.lower()
        matches = set()
        for node in candidates:
            summary = self._graph.function_summary(node)
            route_rules = " ".join(
                route.rule or ""
                for route in summary["routes"]
            )
            haystack = " ".join(
                [
                    node,
                    short_name(node),
                    route_rules,
                    " ".join(summary["keys"]),
                    " ".join(summary["sources"]),
                ]
            ).lower()
            if needle in haystack:
                matches.add(node)
        if matches:
            return self._graph.subgraph_nodes(targets=sorted(matches), radius=1) & candidates
        return set()

    def _visible_nodes(self) -> list[str]:
        candidates = self._candidate_nodes()
        query = self._search.value.strip()
        if query:
            candidates = self._match_nodes(candidates, query)
        return sorted(candidates)

    def _build_display_graph(self) -> nx.DiGraph:
        visible_nodes = self._visible_nodes()
        display = nx.DiGraph()
        for node in visible_nodes:
            summary = self._graph.function_summary(node)
            display.add_node(
                node,
                label=self._node_label(node),
                qualname=node,
                kind=summary["kind"],
                has_access=1 if summary["accesses"] else 0,
                has_merge=1 if summary["merges"] else 0,
            )
        visible_set = set(visible_nodes)
        for src, dst in self._graph.g.edges():
            if src not in visible_set or dst not in visible_set:
                continue
            call_edges = self._graph.call_edges_between(src, dst)
            display.add_edge(
                src,
                dst,
                source=src,
                target=dst,
                call_count=len(call_edges) or 1,
                line=call_edges[0].location.line if call_edges else 0,
            )
        return display

    def _set_layout(self) -> None:
        try:
            self._cyto.set_layout(name=self._layout_picker.value, animate=False)
        except Exception:
            self._cyto.set_layout(name="breadthfirst", animate=False)

    def _apply_classes(self) -> None:
        for node in self._cyto.graph.nodes:
            qualname = node.data.get("qualname")
            classes = []
            if qualname in self._highlighted_nodes:
                classes.append("highlighted")
            if self._selected_node and qualname == self._selected_node:
                classes.append("selected")
            node.classes = " ".join(classes)
        for edge in self._cyto.graph.edges:
            pair = (edge.data.get("source"), edge.data.get("target"))
            classes = []
            if pair in self._highlighted_edges:
                classes.append("highlighted")
            if self._selected_edge == pair:
                classes.append("selected")
            edge.classes = " ".join(classes)

    def _summary_html(self, visible_nodes: list[str]) -> str:
        visible_set = set(visible_nodes)
        visible_endpoints = [node for node in visible_nodes if self._graph.node_kind(node) == "endpoint"]
        visible_edges = sum(
            1
            for src, dst in self._graph.g.edges()
            if src in visible_set and dst in visible_set
        )
        return f"""
        <div style="font-family:system-ui;padding:2px 0 8px 0;color:#475569;font-size:12px">
            {len(visible_nodes)} visible nodes · {visible_edges} visible edges ·
            {len(visible_endpoints)} endpoints in scope
        </div>
        """

    def _selection_html(self, title: str, body: str) -> str:
        return f"""
        <div style="font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;
                    background:#ffffff;padding:10px 12px;color:#0f172a">
          <div style="font-weight:700;font-size:13px;margin-bottom:6px">{title}</div>
          <div style="font-size:12px;color:#334155;line-height:1.5">{body}</div>
        </div>
        """

    def _refresh_graph(self, _change=None) -> None:
        display = self._build_display_graph()
        self._cyto = ipycytoscape.CytoscapeWidget()
        self._cyto.graph.add_graph_from_networkx(display)
        self._cyto.cytoscape_style = list(_STYLE)
        self._cyto.layout = ipywidgets.Layout(
            width="100%",
            height="520px",
            border="1px solid #dbe4f0",
        )
        self._cyto.zoom = 1.0
        self._set_layout()
        self._cyto.on("node", "click", self._handle_node_click)
        self._cyto.on("edge", "click", self._handle_edge_click)
        self._cyto_box.children = (self._cyto,)
        visible_nodes = sorted(display.nodes())
        self._summary.value = self._summary_html(visible_nodes)
        if not self._selection.value:
            self._selection.value = self._selection_html(
                "Selection",
                "Click a node to inspect that function or an edge to inspect a call site.",
            )
        self._apply_classes()

    def _adjust_zoom(self, factor: float) -> None:
        current = float(getattr(self._cyto, "zoom", 1.0) or 1.0)
        min_zoom = float(getattr(self._cyto, "min_zoom", 0.1) or 0.1)
        max_zoom = float(getattr(self._cyto, "max_zoom", 5.0) or 5.0)
        self._cyto.zoom = max(min_zoom, min(max_zoom, current * factor))

    def _handle_node_click(self, event: dict) -> None:
        data = event.get("data", {})
        qualname = data.get("qualname") or data.get("id")
        if not qualname:
            return
        self._selected_node = qualname
        self._selected_edge = None
        summary = self._graph.function_summary(qualname)
        body = (
            f"<div><b>{qualname}</b></div>"
            f"<div>kind: {summary['kind']}</div>"
            f"<div>direct accesses: {len(summary['accesses'])}</div>"
            f"<div>direct callees: {len(summary['callees'])}</div>"
            f"<div>keys: {', '.join(summary['keys']) or 'none'}</div>"
            f"<div>sources: {', '.join(summary['sources']) or 'none'}</div>"
        )
        self._selection.value = self._selection_html("Selected Function", body)
        self._apply_classes()
        for callback in self._callbacks:
            callback(qualname)

    def _handle_edge_click(self, event: dict) -> None:
        data = event.get("data", {})
        pair = (data.get("source"), data.get("target"))
        call_edges = self._graph.call_edges_between(*pair) if all(pair) else []
        self._selected_edge = pair
        self._selected_node = None
        if call_edges:
            lines = ", ".join(str(edge.location.line) for edge in call_edges[:5])
            body = (
                f"<div><b>{pair[0]}</b> &rarr; <b>{pair[1]}</b></div>"
                f"<div>call sites: {len(call_edges)}</div>"
                f"<div>lines: {lines}</div>"
            )
        else:
            body = f"<div><b>{pair[0]}</b> &rarr; <b>{pair[1]}</b></div>"
        self._selection.value = self._selection_html("Selected Edge", body)
        self._apply_classes()
        for callback in self._edge_callbacks:
            for edge in call_edges:
                callback(edge)

    def on_node_click(self, callback: Callable[[str], None]) -> None:
        self._callbacks.append(callback)

    def on_edge_click(self, callback: Callable) -> None:
        self._edge_callbacks.append(callback)

    def show_full_graph(self) -> None:
        self._focus_nodes = None
        self._scope.value = "all"
        self._refresh_graph()

    def highlight_path(self, path: list[str]) -> None:
        for index in range(len(path) - 1):
            self._highlighted_edges.add((path[index], path[index + 1]))
        self._highlighted_nodes.update(path)
        self._apply_classes()

    def highlight_nodes(self, nodes: list[str], color: str | None = None) -> None:
        del color
        self._highlighted_nodes.update(nodes)
        self._apply_classes()

    def reset_highlights(self) -> None:
        self._highlighted_nodes.clear()
        self._highlighted_edges.clear()
        self._selected_node = None
        self._selected_edge = None
        self._apply_classes()

    def focus_nodes(self, nodes: list[str], *, title: str | None = None) -> None:
        self._focus_nodes = set(nodes)
        self._scope.value = "focused"
        self._refresh_graph()
        if title:
            self._selection.value = self._selection_html("Focused Subgraph", title)

    def focus_endpoint(self, handler: str) -> None:
        summary = self._graph.endpoint_summary(handler)
        self._focus_nodes = set(summary["reachable"])
        self._scope.value = "focused"
        self._refresh_graph()
        self.reset_highlights()
        self.highlight_nodes([handler])
        self._selection.value = self._selection_html(
            "Endpoint Focus",
            f"<div><b>{handler}</b></div>"
            f"<div>route: {summary['rule'] or '?'}</div>"
            f"<div>reachable functions: {len(summary['reachable'])}</div>"
            f"<div>sources: {', '.join(summary['sources']) or 'none'}</div>",
        )

    def focus_finding(self, finding) -> None:
        nodes: list[str] = []
        if finding.endpoint is not None:
            nodes.append(finding.endpoint.handler_qualname)
        for evidence in finding.evidence:
            qualname = evidence_qualname(evidence)
            if not qualname:
                continue
            if finding.endpoint is not None:
                path = self._graph.call_path(finding.endpoint.handler_qualname, qualname)
                if path:
                    nodes.extend(path)
                    continue
            nodes.append(qualname)
        unique_nodes = list(OrderedDict.fromkeys(node for node in nodes if node))
        self._focus_nodes = set(unique_nodes)
        self._scope.value = "focused"
        self._refresh_graph()
        self.reset_highlights()
        if unique_nodes:
            self.highlight_nodes(unique_nodes)
        if finding.endpoint is not None:
            for evidence in finding.evidence:
                qualname = evidence_qualname(evidence)
                if not qualname:
                    continue
                path = self._graph.call_path(finding.endpoint.handler_qualname, qualname)
                if path:
                    self.highlight_path(path)
        self._selection.value = self._selection_html(
            "Finding Focus",
            f"<div><b>{finding.rule_id}</b> · {finding.title}</div>"
            f"<div>{len(unique_nodes)} functions in focused subgraph</div>"
            f"<div>{len(finding.evidence)} evidence items</div>",
        )

    @property
    def widget(self):
        return self._container

    def __repr__(self) -> str:
        stats = self._graph.stats()
        return f"GraphView({stats['nodes']} nodes, {stats['edges']} edges)"
