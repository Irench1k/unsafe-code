"""Notebook-friendly list and mapping wrappers for query results."""

from __future__ import annotations

import pprint
from html import escape
from pathlib import Path


def _table_html(title: str, columns: list[str], rows: list[list[str]], *, max_height: str = "320px") -> str:
    header = "".join(
        f"<th style='text-align:left;padding:8px 10px;border-bottom:1px solid #dbe4f0;"
        f"position:sticky;top:0;background:#f8fafc'>{escape(col)}</th>"
        for col in columns
    )
    body = []
    for row in rows:
        body.append(
            "<tr>"
            + "".join(
                f"<td style='text-align:left;padding:8px 10px;border-bottom:1px solid #eef2f7;"
                f"vertical-align:top'>{cell}</td>"
                for cell in row
            )
            + "</tr>"
        )
    return (
        "<div style='font-family:system-ui;border:1px solid #dbe4f0;border-radius:12px;background:#fff'>"
        f"<div style='padding:10px 12px;font-weight:700;font-size:13px;color:#0f172a'>{escape(title)}</div>"
        f"<div style='max-height:{max_height};overflow:auto'>"
        "<table style='width:100%;border-collapse:collapse;font-size:12px;color:#0f172a'>"
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        "</table></div></div>"
    )


class PrettyMapping(dict):
    """Dictionary with prettier repr output."""

    def __repr__(self) -> str:
        return pprint.pformat(dict(self), sort_dicts=False, width=100, compact=False)

    __str__ = __repr__


class StatsView(PrettyMapping):
    """Notebook-friendly stats mapping."""

    def _repr_html_(self) -> str:
        rows = [[escape(str(key)), escape(str(value))] for key, value in self.items()]
        return _table_html("Graph Stats", ["Metric", "Value"], rows, max_height="260px")


class KeyAccessView(PrettyMapping):
    """Notebook-friendly access grouping by key."""

    def _repr_html_(self) -> str:
        rows = []
        for key, accesses in self.items():
            sources = sorted({a.source.value for a in accesses})
            accessors = sorted({a.accessor.value for a in accesses})
            functions = sorted({a.function_qualname.rsplit(".", 1)[-1] for a in accesses})
            preview = escape(accesses[0].raw_code) if accesses else ""
            rows.append(
                [
                    f"<code>{escape(str(key))}</code>",
                    str(len(accesses)),
                    escape(", ".join(sources)),
                    escape(", ".join(accessors)),
                    escape(", ".join(functions[:5])),
                    preview,
                ]
            )
        return _table_html(
            "Accesses Grouped by Key",
            ["Key", "Count", "Sources", "Accessors", "Functions", "Example"],
            rows,
            max_height="360px",
        )


class AccessListView(list):
    """Notebook-friendly access list."""

    def __repr__(self) -> str:
        return pprint.pformat(list(self), width=100, compact=False)

    __str__ = __repr__

    def _repr_html_(self) -> str:
        rows = []
        for access in self:
            rows.append(
                [
                    escape(access.function_qualname),
                    escape(access.source.value),
                    escape(access.accessor.value),
                    escape(access.key_literal or access.key_expr or ""),
                    escape(f"{Path(access.location.file).name}:{access.location.line}"),
                    escape(access.raw_code),
                ]
            )
        return _table_html(
            "Input Accesses",
            ["Function", "Source", "Accessor", "Key", "Location", "Code"],
            rows,
            max_height="360px",
        )


class EndpointDetailView(PrettyMapping):
    """Notebook-friendly endpoint-detail mapping."""

    def _repr_html_(self) -> str:
        rows = []
        for handler, detail in self.items():
            route = detail["route"]
            rows.append(
                [
                    escape(handler),
                    escape(route.rule or ""),
                    escape(",".join(route.methods)),
                    str(len(detail["accesses"])),
                    escape(", ".join(sorted(s.value for s in detail["sources"]))),
                    escape(", ".join(sorted(k for k in detail["keys"]))),
                    str(len(detail["merges"])),
                ]
            )
        return _table_html(
            "Endpoint Detail",
            ["Handler", "Route", "Methods", "Accesses", "Sources", "Keys", "Merges"],
            rows,
            max_height="340px",
        )


class DivergentKeysView(PrettyMapping):
    """Notebook-friendly divergent-key summary."""

    def _repr_html_(self) -> str:
        rows = []
        for key, detail in self.items():
            rows.append(
                [
                    f"<code>{escape(key)}</code>",
                    escape(", ".join(sorted(s.value for s in detail["sources"]))),
                    escape(", ".join(sorted(a.value for a in detail["accessors"]))),
                    str(len(detail["accesses"])),
                ]
            )
        return _table_html(
            "Divergent Keys",
            ["Key", "Sources", "Accessors", "Access Count"],
            rows,
            max_height="320px",
        )
