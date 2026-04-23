"""Interactive findings browser tuned for rule-development workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import ipydatagrid
import ipywidgets
import pandas as pd

from ._common import relative_file_label, short_name

_SEVERITY_BG = {
    "CRITICAL": "#fecaca",
    "HIGH": "#fed7aa",
    "MEDIUM": "#fef3c7",
    "LOW": "#dbeafe",
    "INFO": "#e2e8f0",
}


def _finding_row(finding, target_path: Path | None) -> dict:
    sources = sorted({
        getattr(ev, "source", None).value
        for ev in finding.evidence
        if getattr(ev, "source", None) is not None
    })
    keys = sorted({
        getattr(ev, "key_literal", None)
        for ev in finding.evidence
        if getattr(ev, "key_literal", None)
    })
    endpoint = finding.endpoint
    location = finding.location
    return {
        "severity": finding.severity.value.upper(),
        "rule_id": finding.rule_id,
        "endpoint": endpoint.rule if endpoint is not None and endpoint.rule else short_name(endpoint.handler_qualname) if endpoint else "",
        "title": finding.title,
        "evidence": len(finding.evidence),
        "sources": ", ".join(sources[:4]),
        "keys": ", ".join(keys[:4]),
        "location": f"{relative_file_label(location.file, target_path)}:{location.line}",
    }


class FindingsTable:
    """Filterable findings browser with row selection callbacks."""

    def __init__(self, findings: list, target_path: Path | None = None) -> None:
        self._all_findings = list(findings)
        self._visible_findings = list(findings)
        self._target_path = target_path
        self._callbacks: list[Callable] = []
        self._active_severities: set[str] = set()

        self._summary = ipywidgets.HTML()
        self._severity_chips = ipywidgets.HBox(layout=ipywidgets.Layout(width="100%", flex_flow="row wrap"))
        self._search = ipywidgets.Text(
            placeholder="Filter by rule, title, key, source, or endpoint",
            layout=ipywidgets.Layout(width="100%"),
        )
        self._grid = self._build_grid(self._dataframe(self._visible_findings))

        self._container = ipywidgets.VBox(
            [self._summary, self._severity_chips, self._search, self._grid],
            layout=ipywidgets.Layout(width="100%"),
        )

        self._search.observe(self._apply_filters, names="value")
        self._refresh_summary()

    def _dataframe(self, findings: list) -> pd.DataFrame:
        if not findings:
            return pd.DataFrame(
                columns=[
                    "severity",
                    "rule_id",
                    "endpoint",
                    "title",
                    "evidence",
                    "sources",
                    "keys",
                    "location",
                ]
            )
        return pd.DataFrame(
            [_finding_row(finding, self._target_path) for finding in findings]
        )

    def _build_grid(self, df: pd.DataFrame) -> ipydatagrid.DataGrid:
        grid = ipydatagrid.DataGrid(
            df,
            selection_mode="row",
            header_visibility="column",
            base_row_size=30,
            layout=ipywidgets.Layout(height="280px", width="100%"),
            column_widths={
                "severity": 90,
                "rule_id": 120,
                "endpoint": 160,
                "title": 360,
                "evidence": 80,
                "sources": 130,
                "keys": 130,
                "location": 170,
            },
            renderers={
                "severity": ipydatagrid.TextRenderer(
                    text_color="#0f172a",
                    background_color=ipydatagrid.Expr(
                        '"#fecaca" if cell.value == "CRITICAL"'
                        ' else "#fed7aa" if cell.value == "HIGH"'
                        ' else "#fef3c7" if cell.value == "MEDIUM"'
                        ' else "#dbeafe" if cell.value == "LOW"'
                        ' else "#e2e8f0"'
                    ),
                    font="600 12px system-ui",
                    horizontal_alignment="center",
                ),
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
                "selection_fill_color": "rgba(219, 234, 254, 0.16)",
                "selection_border_color": "#60a5fa",
                "header_background_color": "#e2e8f0",
                "horizontal_grid_line_color": "#e2e8f0",
                "vertical_grid_line_color": "#e2e8f0",
            },
        )
        grid.on_cell_click(self._handle_click)
        return grid

    def _refresh_summary(self) -> None:
        counts = {}
        for finding in self._visible_findings:
            key = finding.severity.value.upper()
            counts[key] = counts.get(key, 0) + 1
        chip_widgets = []
        total_counts = {}
        for finding in self._all_findings:
            sev = finding.severity.value.upper()
            total_counts[sev] = total_counts.get(sev, 0) + 1
        for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
            count = total_counts.get(sev, 0)
            if count == 0:
                continue
            button = ipywidgets.ToggleButton(
                value=sev in self._active_severities,
                description=f"{sev} {count}",
                layout=ipywidgets.Layout(width="auto"),
                tooltip=f"Toggle {sev} findings",
            )
            button.style.button_color = _SEVERITY_BG[sev] if button.value else "#f8fafc"
            button.observe(self._toggle_severity(sev), names="value")
            chip_widgets.append(button)
        self._severity_chips.children = tuple(chip_widgets)
        self._summary.value = (
            "<div style='font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;"
            "background:#ffffff;padding:10px 12px;color:#0f172a'>"
            f"<div style='font-weight:700;font-size:13px;margin-bottom:6px'>Findings</div>"
            f"<div style='font-size:12px;color:#475569;margin-bottom:6px'>"
            f"{len(self._visible_findings)} visible / {len(self._all_findings)} total"
            "</div>"
            "</div>"
        )

    def _toggle_severity(self, severity: str):
        def _handler(change):
            if change["new"]:
                self._active_severities.add(severity)
            else:
                self._active_severities.discard(severity)
            self._apply_filters()
        return _handler

    def _apply_filters(self, _change=None) -> None:
        needle = self._search.value.strip().lower()

        def matches(finding) -> bool:
            if self._active_severities and finding.severity.value.upper() not in self._active_severities:
                return False
            if not needle:
                return True
            haystack = " ".join(
                [
                    finding.rule_id,
                    finding.title,
                    finding.description,
                    finding.endpoint.rule if finding.endpoint and finding.endpoint.rule else "",
                    getattr(finding.endpoint, "handler_qualname", "") if finding.endpoint else "",
                    " ".join(
                        getattr(ev, "key_literal", "") or ""
                        for ev in finding.evidence
                    ),
                    " ".join(
                        getattr(getattr(ev, "source", None), "value", "")
                        for ev in finding.evidence
                    ),
                ]
            ).lower()
            return needle in haystack

        self._visible_findings = [finding for finding in self._all_findings if matches(finding)]
        self._grid.data = self._dataframe(self._visible_findings)
        self._refresh_summary()

    def _handle_click(self, event: dict) -> None:
        row_idx = event.get("primary_key_row")
        if row_idx is None:
            return
        try:
            idx = int(row_idx)
        except (TypeError, ValueError):
            return
        if not (0 <= idx < len(self._visible_findings)):
            return
        finding = self._visible_findings[idx]
        self._grid.clear_selection()
        for callback in self._callbacks:
            callback(finding)

    def on_select(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def update(self, findings: list) -> None:
        self._all_findings = list(findings)
        self._visible_findings = list(findings)
        self._active_severities.clear()
        self._search.value = ""
        self._grid.data = self._dataframe(self._visible_findings)
        self._refresh_summary()

    @property
    def widget(self) -> ipywidgets.VBox:
        return self._container

    def __repr__(self) -> str:
        return f"FindingsTable({len(self._all_findings)} findings)"
