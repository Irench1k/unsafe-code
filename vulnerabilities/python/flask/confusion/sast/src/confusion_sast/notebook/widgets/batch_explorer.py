"""Batch-level wrapper around the interactive Explorer workbench."""

from __future__ import annotations

import ipywidgets

from .explorer import Explorer


class BatchExplorer:
    """Switch between exercises while reusing the Explorer workflow."""

    def __init__(self, graphs: dict, results, *, target_path=None) -> None:
        self._graphs = graphs
        self._results = getattr(results, "_findings", results)
        self._target_path = target_path
        exercise_names = list(self._graphs)
        self._picker = ipywidgets.Dropdown(
            options=exercise_names,
            value=exercise_names[0] if exercise_names else None,
            description="Exercise:",
            layout=ipywidgets.Layout(width="320px"),
        )
        self._summary = ipywidgets.HTML()
        self._body = ipywidgets.Box(layout=ipywidgets.Layout(width="100%"))
        self._container = ipywidgets.VBox([self._summary, self._picker, self._body], layout=ipywidgets.Layout(width="100%"))
        self._picker.observe(self._render_selected, names="value")
        self._render_selected()

    def _render_selected(self, _change=None) -> None:
        name = self._picker.value
        if not name:
            self._summary.value = ""
            self._body.children = ()
            return
        findings = self._results.get(name, [])
        graph = self._graphs[name]
        self._summary.value = (
            "<div style='font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;"
            "background:#ffffff;padding:10px 12px;color:#0f172a'>"
            f"<div style='font-weight:700;font-size:13px'>{name}</div>"
            f"<div style='font-size:12px;color:#475569'>{len(findings)} findings for this exercise</div>"
            "</div>"
        )
        self._body.children = (Explorer(graph, findings, target_path=self._target_path).widget,)

    @property
    def widget(self):
        return self._container

    def _repr_mimebundle_(self, **kwargs):
        return self._container._repr_mimebundle_(**kwargs)
