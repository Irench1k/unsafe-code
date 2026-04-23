"""Interactive evidence browser for the current finding or function."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import ipydatagrid
import ipywidgets
import pandas as pd

from ._common import evidence_location, evidence_qualname, relative_file_label, short_name


def _row(evidence, target_path: Path | None) -> dict:
    loc = evidence_location(evidence)
    return {
        "type": type(evidence).__name__,
        "function": short_name(evidence_qualname(evidence)),
        "source": getattr(getattr(evidence, "source", None), "value", ""),
        "accessor": getattr(getattr(evidence, "accessor", None), "value", ""),
        "key": getattr(evidence, "key_literal", None) or getattr(evidence, "key_expr", None) or "",
        "location": f"{relative_file_label(loc.file, target_path) if loc else ''}:{loc.line if loc else ''}",
        "preview": (getattr(evidence, "raw_code", None) or "")[:100],
    }


class EvidenceTable:
    """Row-selectable evidence list."""

    def __init__(self, *, target_path: Path | None = None) -> None:
        self._target_path = target_path
        self._evidence: list = []
        self._callbacks: list[Callable] = []
        self._summary = ipywidgets.HTML()
        self._grid = self._build_grid(self._dataframe([]))
        self._container = ipywidgets.VBox([self._summary, self._grid])
        self.update([], title="Evidence")

    def _dataframe(self, evidence: list) -> pd.DataFrame:
        if not evidence:
            return pd.DataFrame(
                columns=["type", "function", "source", "accessor", "key", "location", "preview"]
            )
        return pd.DataFrame([_row(item, self._target_path) for item in evidence])

    def _build_grid(self, df: pd.DataFrame) -> ipydatagrid.DataGrid:
        grid = ipydatagrid.DataGrid(
            df,
            selection_mode="row",
            header_visibility="column",
            base_row_size=30,
            layout=ipywidgets.Layout(height="220px", width="100%"),
            column_widths={
                "type": 120,
                "function": 160,
                "source": 90,
                "accessor": 90,
                "key": 120,
                "location": 160,
                "preview": 320,
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
                "selection_fill_color": "rgba(237, 233, 254, 0.16)",
                "selection_border_color": "#8b5cf6",
                "header_background_color": "#e2e8f0",
                "horizontal_grid_line_color": "#e2e8f0",
                "vertical_grid_line_color": "#e2e8f0",
            },
        )
        grid.on_cell_click(self._handle_click)
        return grid

    def _handle_click(self, event: dict) -> None:
        row_idx = event.get("primary_key_row")
        if row_idx is None:
            return
        try:
            idx = int(row_idx)
        except (TypeError, ValueError):
            return
        if not (0 <= idx < len(self._evidence)):
            return
        evidence = self._evidence[idx]
        self._grid.clear_selection()
        for callback in self._callbacks:
            callback(evidence)

    def on_select(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def update(self, evidence: list, *, title: str) -> None:
        self._evidence = list(evidence)
        self._grid.data = self._dataframe(self._evidence)
        self._summary.value = (
            "<div style='font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;"
            "background:#ffffff;padding:10px 12px;color:#0f172a'>"
            f"<div style='font-weight:700;font-size:13px;margin-bottom:6px'>{title}</div>"
            f"<div style='font-size:12px;color:#475569'>{len(self._evidence)} items</div>"
            "</div>"
        )

    @property
    def widget(self) -> ipywidgets.VBox:
        return self._container
