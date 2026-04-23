"""HTML detail pane for notebook exploration."""

from __future__ import annotations

from pathlib import Path

import ipywidgets

from ._common import evidence_location, evidence_qualname, relative_file_label, short_name


class DetailsPane:
    """Rich HTML summary panel for the current selection."""

    def __init__(self, *, target_path: Path | None = None, title: str = "Details") -> None:
        self._target_path = target_path
        self._title = title
        self._html = ipywidgets.HTML()
        self.show_message("Select a finding, endpoint, node, or evidence item.")

    @property
    def widget(self) -> ipywidgets.HTML:
        return self._html

    def show_message(self, message: str) -> None:
        self._html.value = f"""
        <div style="font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;
                    background:#f8fbff;padding:14px 16px;color:#334155">
          <div style="font-weight:700;font-size:13px;margin-bottom:6px">{self._title}</div>
          <div style="font-size:13px;line-height:1.45">{message}</div>
        </div>
        """

    def show_finding(self, finding) -> None:
        endpoint = finding.endpoint
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
        evidence_rows = []
        for ev in finding.evidence:
            loc = evidence_location(ev)
            label = getattr(ev, "raw_code", None) or type(ev).__name__
            evidence_rows.append(
                "<tr>"
                f"<td style='padding:6px 8px;vertical-align:top'>{type(ev).__name__}</td>"
                f"<td style='padding:6px 8px;vertical-align:top;font-family:monospace'>{short_name(evidence_qualname(ev))}</td>"
                f"<td style='padding:6px 8px;vertical-align:top'>{relative_file_label(loc.file, self._target_path) if loc else ''}:{loc.line if loc else ''}</td>"
                f"<td style='padding:6px 8px;vertical-align:top'>{label[:120]}</td>"
                "</tr>"
            )
        endpoint_html = ""
        if endpoint is not None:
            endpoint_html = (
                "<div style='margin-top:8px;font-size:13px;color:#334155'>"
                f"<b>Endpoint:</b> {'/'.join(endpoint.methods)} {endpoint.rule or '?'}"
                f" <span style='color:#64748b'>({short_name(endpoint.handler_qualname)})</span>"
                "</div>"
            )
        chips = []
        for source in sources:
            chips.append(
                f"<span style='display:inline-block;padding:2px 8px;border-radius:999px;"
                f"background:#dbeafe;color:#1d4ed8;font-size:11px;margin-right:6px'>{source}</span>"
            )
        for key in keys:
            chips.append(
                f"<span style='display:inline-block;padding:2px 8px;border-radius:999px;"
                f"background:#dcfce7;color:#166534;font-size:11px;margin-right:6px'>{key}</span>"
            )
        self._html.value = f"""
        <div style="font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;
                    background:#ffffff;padding:14px 16px;color:#0f172a">
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
            <span style="padding:2px 10px;border-radius:999px;background:#0f172a;color:white;
                         font-size:11px;font-weight:700">{finding.rule_id}</span>
            <span style="padding:2px 10px;border-radius:999px;background:#fef3c7;color:#92400e;
                         font-size:11px;font-weight:700">{finding.severity.value.upper()}</span>
            <span style="font-weight:700;font-size:14px">{finding.title}</span>
          </div>
          {endpoint_html}
          <div style="margin-top:10px;font-size:13px;line-height:1.5;color:#334155">
            {finding.description}
          </div>
          <div style="margin-top:10px">{''.join(chips)}</div>
          <div style="margin-top:12px;font-weight:700;font-size:13px">Evidence</div>
          <table style="width:100%;border-collapse:collapse;margin-top:6px;font-size:12px">
            <thead>
              <tr style="background:#f8fafc;color:#475569;text-align:left">
                <th style="padding:6px 8px">Type</th>
                <th style="padding:6px 8px">Function</th>
                <th style="padding:6px 8px">Location</th>
                <th style="padding:6px 8px">Preview</th>
              </tr>
            </thead>
            <tbody>{''.join(evidence_rows)}</tbody>
          </table>
        </div>
        """

    def show_endpoint(self, summary: dict) -> None:
        route = summary.get("route")
        self._html.value = f"""
        <div style="font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;
                    background:#ffffff;padding:14px 16px;color:#0f172a">
          <div style="font-weight:700;font-size:14px">{short_name(summary['handler'])}</div>
          <div style="margin-top:6px;color:#334155;font-size:13px">
            <b>Route:</b> {'/'.join(summary['methods']) or '?'} {route.rule if route else '?'}
          </div>
          <div style="margin-top:10px;display:grid;grid-template-columns:repeat(4, minmax(0, 1fr));
                      gap:8px;font-size:12px">
            <div style="padding:8px;border-radius:10px;background:#f8fafc"><b>{summary['access_count']}</b><br>reachable accesses</div>
            <div style="padding:8px;border-radius:10px;background:#f8fafc"><b>{summary['merge_count']}</b><br>dict merges</div>
            <div style="padding:8px;border-radius:10px;background:#f8fafc"><b>{summary['middleware_count']}</b><br>middleware hooks</div>
            <div style="padding:8px;border-radius:10px;background:#f8fafc"><b>{len(summary['reachable'])}</b><br>reachable functions</div>
          </div>
          <div style="margin-top:10px;font-size:12px;color:#475569"><b>Sources:</b> {', '.join(summary['sources']) or 'none'}</div>
          <div style="margin-top:6px;font-size:12px;color:#475569"><b>Keys:</b> {', '.join(summary['keys']) or 'none'}</div>
          <div style="margin-top:6px;font-size:12px;color:#475569"><b>Accessors:</b> {', '.join(summary['accessors']) or 'none'}</div>
        </div>
        """

    def show_function(self, summary: dict) -> None:
        loc = summary.get("location")
        self._html.value = f"""
        <div style="font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;
                    background:#ffffff;padding:14px 16px;color:#0f172a">
          <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
            <span style="padding:2px 8px;border-radius:999px;background:#e2e8f0;color:#334155;
                         font-size:11px;font-weight:700">{summary['kind']}</span>
            <span style="font-weight:700;font-size:14px">{summary['qualname']}</span>
          </div>
          <div style="margin-top:8px;font-size:12px;color:#475569">
            {relative_file_label(loc.file, self._target_path) if loc else 'unknown'}:{loc.line if loc else ''}
          </div>
          <div style="margin-top:10px;display:grid;grid-template-columns:repeat(4, minmax(0, 1fr));
                      gap:8px;font-size:12px">
            <div style="padding:8px;border-radius:10px;background:#f8fafc"><b>{len(summary['accesses'])}</b><br>direct accesses</div>
            <div style="padding:8px;border-radius:10px;background:#f8fafc"><b>{len(summary['merges'])}</b><br>dict merges</div>
            <div style="padding:8px;border-radius:10px;background:#f8fafc"><b>{len(summary['callers'])}</b><br>callers</div>
            <div style="padding:8px;border-radius:10px;background:#f8fafc"><b>{len(summary['callees'])}</b><br>callees</div>
          </div>
          <div style="margin-top:10px;font-size:12px;color:#475569"><b>Sources:</b> {', '.join(summary['sources']) or 'none'}</div>
          <div style="margin-top:6px;font-size:12px;color:#475569"><b>Keys:</b> {', '.join(summary['keys']) or 'none'}</div>
          <div style="margin-top:6px;font-size:12px;color:#475569"><b>Direct callees:</b> {', '.join(short_name(v) for v in summary['callees']) or 'none'}</div>
        </div>
        """

    def show_edge(self, edge) -> None:
        location = edge.location
        self._html.value = f"""
        <div style="font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;
                    background:#ffffff;padding:14px 16px;color:#0f172a">
          <div style="font-weight:700;font-size:14px">Call Edge</div>
          <div style="margin-top:8px;font-size:13px;color:#334155">
            <span style="font-family:monospace">{edge.caller_qualname}</span>
            &nbsp;&rarr;&nbsp;
            <span style="font-family:monospace">{edge.callee_qualname}</span>
          </div>
          <div style="margin-top:8px;font-size:12px;color:#475569">
            {relative_file_label(location.file, self._target_path)}:{location.line}
          </div>
        </div>
        """

    def show_evidence(self, evidence) -> None:
        location = evidence_location(evidence)
        source = getattr(getattr(evidence, "source", None), "value", "")
        accessor = getattr(getattr(evidence, "accessor", None), "value", "")
        key = getattr(evidence, "key_literal", None) or getattr(evidence, "key_expr", None) or ""
        raw_code = getattr(evidence, "raw_code", None) or type(evidence).__name__
        self._html.value = f"""
        <div style="font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;
                    background:#ffffff;padding:14px 16px;color:#0f172a">
          <div style="font-weight:700;font-size:14px">Evidence</div>
          <div style="margin-top:8px;font-size:12px;color:#475569">
            {type(evidence).__name__} · {short_name(evidence_qualname(evidence))}
          </div>
          <div style="margin-top:8px;font-size:12px;color:#475569">
            {relative_file_label(location.file, self._target_path) if location else ''}:{location.line if location else ''}
          </div>
          <div style="margin-top:10px;font-size:12px;color:#475569"><b>Source:</b> {source or 'n/a'}</div>
          <div style="margin-top:6px;font-size:12px;color:#475569"><b>Accessor:</b> {accessor or 'n/a'}</div>
          <div style="margin-top:6px;font-size:12px;color:#475569"><b>Key:</b> {key or 'n/a'}</div>
          <div style="margin-top:10px;padding:8px;border-radius:10px;background:#f8fafc;
                      font-family:monospace;font-size:12px;color:#0f172a">{raw_code}</div>
        </div>
        """
