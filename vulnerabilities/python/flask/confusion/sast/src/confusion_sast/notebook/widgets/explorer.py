"""Domain-specific analysis workbench for confusion SAST notebooks."""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import ipywidgets

from ._common import evidence_qualname, short_name
from .code_path_view import CodePathView
from .details_pane import DetailsPane
from .endpoint_table import EndpointTable
from .evidence_table import EvidenceTable
from .findings_table import FindingsTable
from .graph_view import GraphView


class Explorer:
    """Synchronized notebook workbench for findings, graph, and source context."""

    def __init__(self, graph_or_scan, findings: list | object | None = None, target_path: Path | None = None) -> None:
        if hasattr(graph_or_scan, "graph") and hasattr(graph_or_scan, "findings"):
            scan_result = graph_or_scan
            self._graph = scan_result.graph
            base_findings = scan_result.findings
            derived_target = getattr(scan_result, "target", None)
        else:
            self._graph = graph_or_scan
            base_findings = []
            derived_target = getattr(self._graph, "target_root", None)

        if findings is None:
            self._findings = list(base_findings)
        elif hasattr(findings, "findings"):
            self._findings = list(findings.findings)
        else:
            self._findings = list(findings)

        self._target_path = target_path or derived_target or getattr(self._graph, "target_root", None)
        self._active_finding = None

        self._findings_table = FindingsTable(self._findings, target_path=self._target_path)
        self._endpoint_table = EndpointTable(self._graph, target_path=self._target_path)
        self._graph_view = GraphView(self._graph)
        self._details = DetailsPane(target_path=self._target_path)
        self._evidence_table = EvidenceTable(target_path=self._target_path)
        self._code_path = CodePathView(target_path=self._target_path)

        self._findings_table.on_select(self._on_finding_selected)
        self._endpoint_table.on_select(self._on_endpoint_selected)
        self._graph_view.on_node_click(self._on_node_clicked)
        self._graph_view.on_edge_click(self._on_edge_clicked)
        self._evidence_table.on_select(self._on_evidence_selected)

        self._container = self._build_layout()

        if self._findings:
            self._on_finding_selected(self._findings[0])
        elif self._graph.endpoint_handlers():
            self._on_endpoint_selected(self._graph.endpoint_summary(self._graph.endpoint_handlers()[0]))

    def _build_layout(self):
        nav_tabs = ipywidgets.Tab(children=[self._findings_table.widget, self._endpoint_table.widget])
        nav_tabs.set_title(0, "Findings")
        nav_tabs.set_title(1, "Endpoints")
        nav_tabs.layout = ipywidgets.Layout(width="34%", min_width="350px")

        graph_and_details = ipywidgets.HBox(
            [self._graph_view.widget, self._details.widget],
            layout=ipywidgets.Layout(width="66%"),
        )
        self._graph_view.widget.layout = ipywidgets.Layout(width="72%")
        self._details.widget.layout = ipywidgets.Layout(width="28%")

        top = ipywidgets.HBox([nav_tabs, graph_and_details], layout=ipywidgets.Layout(width="100%"))
        bottom = ipywidgets.VBox(
            [self._evidence_table.widget, self._code_path.widget],
            layout=ipywidgets.Layout(width="100%"),
        )
        return ipywidgets.VBox([top, bottom], layout=ipywidgets.Layout(width="100%"))

    def _interesting_endpoint_nodes(self, summary: dict) -> list[str]:
        nodes = [summary["handler"]]
        for qualname in summary["reachable"]:
            if qualname == summary["handler"]:
                continue
            if self._graph.accesses_in(qualname) or self._graph.merges_in(qualname):
                nodes.append(qualname)
        return list(OrderedDict.fromkeys(nodes))

    def _highlight_evidence(self, evidence) -> None:
        qualname = evidence_qualname(evidence)
        self._graph_view.reset_highlights()
        if self._active_finding and self._active_finding.endpoint and qualname:
            path = self._graph.call_path(self._active_finding.endpoint.handler_qualname, qualname)
            if path:
                self._graph_view.highlight_path(path)
                self._graph_view.focus_nodes(path, title="Focused on selected evidence path.")
                self._code_path.show_path(
                    self._graph,
                    path,
                    title=f"Evidence Path · {type(evidence).__name__}",
                    subtitle=getattr(evidence, "raw_code", "")[:120],
                )
                return
        if qualname:
            self._graph_view.highlight_nodes([qualname])
            self._code_path.show_function(self._graph, qualname)

    def _on_finding_selected(self, finding) -> None:
        self._active_finding = finding
        self._details.show_finding(finding)
        self._evidence_table.update(
            finding.evidence,
            title=f"Evidence · {finding.rule_id} ({len(finding.evidence)} items)",
        )
        self._graph_view.focus_finding(finding)
        self._code_path.show_finding(self._graph, finding)

    def _on_endpoint_selected(self, summary: dict) -> None:
        self._active_finding = None
        self._details.show_endpoint(summary)
        evidence = list(summary["accesses"]) + list(summary["merges"]) + list(summary["middleware"])
        self._evidence_table.update(
            evidence,
            title=f"Endpoint Facts · {short_name(summary['handler'])}",
        )
        self._graph_view.focus_endpoint(summary["handler"])
        self._code_path.show_nodes(
            self._graph,
            self._interesting_endpoint_nodes(summary),
            title=f"Endpoint Context · {summary['handler']}",
            subtitle=(
                f"{summary['access_count']} reachable accesses · "
                f"{summary['merge_count']} dict merges"
            ),
            selected_node=summary["handler"],
        )

    def _on_node_clicked(self, qualname: str) -> None:
        summary = self._graph.function_summary(qualname)
        self._details.show_function(summary)
        evidence = list(summary["routes"]) + list(summary["accesses"]) + list(summary["merges"]) + list(summary["before_requests"])
        self._evidence_table.update(
            evidence,
            title=f"Function Facts · {short_name(qualname)}",
        )
        self._code_path.show_function(self._graph, qualname)

    def _on_edge_clicked(self, edge) -> None:
        self._details.show_edge(edge)
        self._code_path.show_nodes(
            self._graph,
            [edge.caller_qualname, edge.callee_qualname],
            title="Call Edge Context",
            subtitle=f"Call site line {edge.location.line}",
            selected_node=edge.caller_qualname,
        )

    def _on_evidence_selected(self, evidence) -> None:
        self._details.show_evidence(evidence)
        self._highlight_evidence(evidence)

    @property
    def widget(self):
        return self._container

    @property
    def findings_table(self) -> FindingsTable:
        return self._findings_table

    @property
    def endpoint_table(self) -> EndpointTable:
        return self._endpoint_table

    @property
    def graph_view(self) -> GraphView:
        return self._graph_view

    @property
    def evidence_table(self) -> EvidenceTable:
        return self._evidence_table

    @property
    def code_path_view(self) -> CodePathView:
        return self._code_path

    def _repr_mimebundle_(self, **kwargs):
        return self._container._repr_mimebundle_(**kwargs)

    def __repr__(self) -> str:
        return (
            f"Explorer({len(self._findings)} findings, "
            f"{self._graph.stats()['nodes']} graph nodes)"
        )
