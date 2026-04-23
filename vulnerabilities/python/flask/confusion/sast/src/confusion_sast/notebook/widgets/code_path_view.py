"""Multi-view source browser for handlers, call paths, and evidence."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import ipywidgets

from ._common import evidence_location, evidence_qualname, relative_file_label, short_name
from .code_viewer import CodeViewer


class CodePathView:
    """Stack of synchronized code viewers representing a code path."""

    def __init__(self, *, target_path: Path | None = None) -> None:
        self._target_path = target_path
        self._header = ipywidgets.HTML()
        self._stack = ipywidgets.Accordion(children=())
        self._container = ipywidgets.VBox(
            [self._header, self._stack],
            layout=ipywidgets.Layout(width="100%"),
        )
        self.clear()

    @property
    def widget(self) -> ipywidgets.VBox:
        return self._container

    def clear(self) -> None:
        self._header.value = """
        <div style="font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;
                    background:#f8fbff;padding:10px 12px;color:#334155;font-size:13px">
          Code context will appear here as you explore findings, endpoints, and functions.
        </div>
        """
        self._stack.children = ()
        self._stack.selected_index = None

    def _line_annotations(self, graph, qualname: str) -> dict[int, list[str]]:
        annotations: dict[int, list[str]] = {}
        for route in graph.routes_for_handler(qualname):
            annotations.setdefault(route.location.line, []).append(
                f"route {'/'.join(route.methods)} {route.rule or '?'}"
            )
        for access in graph.accesses_in(qualname):
            key = access.key_literal or access.key_expr or "dynamic"
            annotations.setdefault(access.location.line, []).append(
                f"{access.source.value}.{access.accessor.value}({key})"
            )
        for merge in graph.merges_in(qualname):
            annotations.setdefault(merge.location.line, []).append("dict merge")
        for before in graph.before_requests:
            if before.function_qualname == qualname:
                annotations.setdefault(before.location.line, []).append("before_request")
        for edge in graph.call_edges_from(qualname):
            annotations.setdefault(edge.location.line, []).append(
                f"calls {short_name(edge.callee_qualname)}"
            )
        return annotations

    def _context_entries(self, graph, nodes: list[str]) -> list[tuple[str, str, int, dict[int, list[str]]]]:
        entries = []
        for qualname in nodes:
            loc = graph.node_primary_location(qualname)
            if loc is None:
                continue
            entries.append(
                (
                    qualname,
                    loc.file,
                    loc.line,
                    self._line_annotations(graph, qualname),
                )
            )
        return entries

    def show_nodes(
        self,
        graph,
        nodes: list[str],
        *,
        title: str,
        subtitle: str = "",
        selected_node: str | None = None,
    ) -> None:
        unique_nodes = list(OrderedDict.fromkeys(node for node in nodes if node))
        entries = self._context_entries(graph, unique_nodes)
        if not entries:
            self.clear()
            return

        self._header.value = f"""
        <div style="font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;
                    background:#ffffff;padding:10px 12px;color:#0f172a">
          <div style="font-weight:700;font-size:13px">{title}</div>
          <div style="margin-top:4px;font-size:12px;color:#475569">{subtitle}</div>
        </div>
        """

        viewers = []
        active_index = 0
        for index, (qualname, file_path, focus_line, annotations) in enumerate(entries):
            viewer = CodeViewer()
            viewer.show_file(
                file_path,
                highlight_lines=sorted(annotations),
                focus_line=focus_line,
                title=f"{index + 1}. {qualname}",
                status_text=relative_file_label(file_path, self._target_path),
                annotations=annotations,
            )
            viewers.append(viewer)
            if selected_node and qualname == selected_node:
                active_index = index

        self._stack.children = tuple(viewers)
        for index, (qualname, _, _, _) in enumerate(entries):
            self._stack.set_title(index, f"{index + 1}. {short_name(qualname)}")
        self._stack.selected_index = active_index

    def show_function(self, graph, qualname: str) -> None:
        summary = graph.function_summary(qualname)
        subtitle = (
            f"{summary['kind']} · "
            f"{len(summary['accesses'])} direct accesses · "
            f"{len(summary['callees'])} callees"
        )
        self.show_nodes(
            graph,
            [qualname],
            title=f"Function Context · {qualname}",
            subtitle=subtitle,
            selected_node=qualname,
        )

    def show_path(self, graph, path: list[str], *, title: str, subtitle: str = "") -> None:
        self.show_nodes(
            graph,
            path,
            title=title,
            subtitle=subtitle,
            selected_node=path[-1] if path else None,
        )

    def show_finding(self, graph, finding) -> None:
        nodes: list[str] = []
        if finding.endpoint is not None:
            nodes.append(finding.endpoint.handler_qualname)

        for evidence in finding.evidence:
            qualname = evidence_qualname(evidence)
            if not qualname:
                continue
            if finding.endpoint is not None:
                path = graph.call_path(finding.endpoint.handler_qualname, qualname)
                if path:
                    nodes.extend(path)
                    continue
            nodes.append(qualname)

        if not nodes and evidence_location(finding):
            loc = evidence_location(finding)
            viewer = CodeViewer()
            viewer.show_location(loc, title=f"{finding.rule_id} · {finding.title}")
            self._header.value = """
            <div style="font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;
                        background:#ffffff;padding:10px 12px;color:#0f172a;font-weight:700;font-size:13px">
              Finding Context
            </div>
            """
            self._stack.children = (viewer,)
            self._stack.set_title(0, "1. finding")
            self._stack.selected_index = 0
            return

        self.show_nodes(
            graph,
            nodes,
            title=f"{finding.rule_id} · {finding.title}",
            subtitle=(
                f"{len(finding.evidence)} evidence items · "
                f"{len(OrderedDict.fromkeys(nodes))} code contexts"
            ),
            selected_node=evidence_qualname(finding.evidence[0]) if finding.evidence else None,
        )
