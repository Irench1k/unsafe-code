"""Interactive endpoint browser for graph exploration."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import ipydatagrid
import ipywidgets
import pandas as pd

from ._common import short_name


def _endpoint_row(summary: dict) -> dict:
    return {
        "methods": ",".join(summary["methods"]) or "?",
        "route": summary["route"].rule if summary["route"] else "",
        "handler": short_name(summary["handler"]),
        "accesses": summary["access_count"],
        "sources": ", ".join(summary["sources"][:4]),
        "keys": ", ".join(summary["keys"][:4]),
        "merges": summary["merge_count"],
        "middleware": summary["middleware_count"],
    }


class EndpointTable:
    """Filterable endpoint table that emits endpoint summaries on selection."""

    def __init__(self, graph, target_path: Path | None = None) -> None:
        self._graph = graph
        self._target_path = target_path
        self._all_summaries = graph.endpoint_summaries()
        self._visible_summaries = list(self._all_summaries)
        self._callbacks: list[Callable] = []

        self._summary = ipywidgets.HTML()
        self._search = ipywidgets.Text(
            placeholder="Filter by route, handler, source, or key",
            layout=ipywidgets.Layout(width="100%"),
        )
        self._grid = self._build_grid(self._dataframe(self._visible_summaries))
        self._container = ipywidgets.VBox([self._summary, self._search, self._grid])

        self._search.observe(self._apply_filters, names="value")
        self._refresh_summary()

    def _dataframe(self, summaries: list[dict]) -> pd.DataFrame:
        if not summaries:
            return pd.DataFrame(
                columns=["methods", "route", "handler", "accesses", "sources", "keys", "merges", "middleware"]
            )
        return pd.DataFrame([_endpoint_row(summary) for summary in summaries])

    def _build_grid(self, df: pd.DataFrame) -> ipydatagrid.DataGrid:
        grid = ipydatagrid.DataGrid(
            df,
            selection_mode="row",
            header_visibility="column",
            base_row_size=30,
            layout=ipywidgets.Layout(height="260px", width="100%"),
            column_widths={
                "methods": 100,
                "route": 180,
                "handler": 180,
                "accesses": 80,
                "sources": 130,
                "keys": 150,
                "merges": 70,
                "middleware": 90,
            },
            default_renderer=ipydatagrid.TextRenderer(
                text_color="#0f172a",
                background_color="#ffffff",
                font="12px system-ui",
            ),
            header_renderer=ipydatagrid.TextRenderer(
                text_color="#0f172a",
                background_color="#e2e8f0",
                font="600 12px system-ui",
                horizontal_alignment="center",
            ),
            grid_style={
                "background_color": "#ffffff",
                "selection_fill_color": "rgba(220, 252, 231, 0.16)",
                "selection_border_color": "#22c55e",
                "header_background_color": "#e2e8f0",
                "horizontal_grid_line_color": "#e2e8f0",
                "vertical_grid_line_color": "#e2e8f0",
            },
        )
        grid.on_cell_click(self._handle_click)
        return grid

    def _refresh_summary(self) -> None:
        self._summary.value = (
            "<div style='font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;"
            "background:#ffffff;padding:10px 12px;color:#0f172a'>"
            "<div style='font-weight:700;font-size:13px;margin-bottom:6px'>Endpoints</div>"
            f"<div style='font-size:12px;color:#475569'>{len(self._visible_summaries)} visible / "
            f"{len(self._all_summaries)} total endpoint handlers</div>"
            "</div>"
        )

    def _apply_filters(self, _change=None) -> None:
        needle = self._search.value.strip().lower()
        if not needle:
            self._visible_summaries = list(self._all_summaries)
        else:
            self._visible_summaries = [
                summary
                for summary in self._all_summaries
                if needle in " ".join(
                    [
                        summary["handler"],
                        summary["route"].rule if summary["route"] and summary["route"].rule else "",
                        " ".join(summary["sources"]),
                        " ".join(summary["keys"]),
                    ]
                ).lower()
            ]
        self._grid.data = self._dataframe(self._visible_summaries)
        self._refresh_summary()

    def _handle_click(self, event: dict) -> None:
        row_idx = event.get("primary_key_row")
        if row_idx is None:
            return
        try:
            idx = int(row_idx)
        except (TypeError, ValueError):
            return
        if not (0 <= idx < len(self._visible_summaries)):
            return
        summary = self._visible_summaries[idx]
        self._grid.clear_selection()
        for callback in self._callbacks:
            callback(summary)

    def on_select(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    @property
    def widget(self) -> ipywidgets.VBox:
        return self._container
