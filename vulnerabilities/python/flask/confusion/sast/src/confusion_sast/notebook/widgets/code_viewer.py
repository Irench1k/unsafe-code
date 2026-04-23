"""Notebook-oriented full-file source viewer.

The confusion SAST workflow is fundamentally about grounding abstract graph
facts back in real code. This widget therefore optimizes for stable source
orientation over generic snippet rendering:

- load the full file, not an extracted slice
- preserve syntax highlighting across the full document
- auto-scroll to the relevant line(s)
- annotate multiple evidence lines simultaneously
- keep a narrow, resizable viewport with native scrollbars
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import anywidget
import traitlets
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer, get_lexer_by_name, guess_lexer_for_filename
from pygments.util import ClassNotFound

if TYPE_CHECKING:
    from ...models import Finding, Location


_ESM = """\
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function renderCode(el, model) {
  const renderedLines = model.get("rendered_lines") || [];
  const fileName = model.get("file_name");
  const title = model.get("title");
  const status = model.get("status_text");
  const highlightLines = new Set(model.get("highlight_lines") || []);
  const focusLine = model.get("focus_line") || 0;
  const selectedLine = model.get("selected_line") || 0;
  const annotations = JSON.parse(model.get("annotations_json") || "{}");

  const root = el.querySelector(".cv-shell");
  if (!root) {
    return;
  }

  if (!renderedLines.length) {
    root.innerHTML = `<div class="cv-empty">No file loaded</div>`;
    return;
  }

  const headerBits = [];
  if (title) {
    headerBits.push(`<div class="cv-title">${escapeHtml(title)}</div>`);
  }
  if (fileName) {
    headerBits.push(`<div class="cv-file">${escapeHtml(fileName)}</div>`);
  }
  if (status) {
    headerBits.push(`<div class="cv-status">${escapeHtml(status)}</div>`);
  }

  const lineEls = renderedLines.map((html, i) => {
    const lineNum = i + 1;
    const classes = ["cv-line"];
    if (highlightLines.has(lineNum)) classes.push("cv-highlight");
    if (lineNum === focusLine) classes.push("cv-focus");
    if (lineNum === selectedLine) classes.push("cv-selected");

    const badges = (annotations[String(lineNum)] || [])
      .map((label) => `<span class="cv-badge">${escapeHtml(label)}</span>`)
      .join("");

    return (
      `<div class="${classes.join(" ")}" data-line="${lineNum}">` +
      `<span class="cv-gutter">${lineNum}</span>` +
      `<span class="cv-code">${html || "&nbsp;"}</span>` +
      `<span class="cv-badges">${badges}</span>` +
      `</div>`
    );
  });

  root.innerHTML =
    `<div class="cv-header">${headerBits.join("")}</div>` +
    `<div class="cv-scroll">${lineEls.join("")}</div>`;

  const scroll = root.querySelector(".cv-scroll");
  const active =
    root.querySelector(`.cv-line[data-line="${selectedLine}"]`) ||
    root.querySelector(`.cv-line[data-line="${focusLine}"]`) ||
    root.querySelector(".cv-highlight");

  if (scroll && active) {
    const targetTop = active.offsetTop - scroll.clientHeight / 2 + active.clientHeight / 2;
    scroll.scrollTop = Math.max(0, targetTop);
  }
}

export function render({ model, el }) {
  el.classList.add("cv-root");

  const style = document.createElement("style");
  style.textContent = `
    .cv-root {
      min-width: 320px;
      min-height: 240px;
      width: 100%;
      height: 100%;
      color: #e6e9ef;
    }
    .cv-shell {
      height: 100%;
      min-height: 240px;
      width: 100%;
      background: #111827;
      border: 1px solid #243244;
      border-radius: 12px;
      overflow: hidden;
      resize: both;
      display: flex;
      flex-direction: column;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
      font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
    }
    .cv-header {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
      gap: 4px;
      padding: 10px 12px;
      background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
      border-bottom: 1px solid #243244;
    }
    .cv-title {
      color: #f8fafc;
      font: 600 13px/1.3 system-ui, sans-serif;
    }
    .cv-file {
      color: #94a3b8;
      font: 500 12px/1.3 system-ui, sans-serif;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .cv-status {
      color: #7dd3fc;
      font: 500 11px/1.3 system-ui, sans-serif;
    }
    .cv-scroll {
      flex: 1 1 auto;
      overflow: auto;
      min-height: 180px;
      background:
        linear-gradient(90deg, rgba(15, 23, 42, 0.98) 0 72px, rgba(17, 24, 39, 0.98) 72px);
    }
    .cv-line {
      display: grid;
      grid-template-columns: 64px minmax(0, 1fr) auto;
      align-items: start;
      min-height: 1.55rem;
      border-left: 3px solid transparent;
      padding-right: 8px;
    }
    .cv-line:hover {
      background: rgba(51, 65, 85, 0.28);
    }
    .cv-highlight {
      background: rgba(245, 158, 11, 0.12);
      border-left-color: #f59e0b;
    }
    .cv-focus {
      background: rgba(34, 197, 94, 0.14);
      border-left-color: #22c55e;
    }
    .cv-selected {
      background: rgba(56, 189, 248, 0.16);
      border-left-color: #38bdf8;
    }
    .cv-gutter {
      color: #64748b;
      user-select: none;
      text-align: right;
      padding: 0.15rem 12px 0.15rem 0;
      font-size: 12px;
      line-height: 1.55rem;
    }
    .cv-code {
      white-space: pre;
      overflow-x: visible;
      min-width: 0;
      padding: 0.15rem 0;
      font-size: 12.5px;
      line-height: 1.55rem;
    }
    .cv-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      justify-content: flex-end;
      padding: 0.25rem 0 0.25rem 8px;
    }
    .cv-badge {
      border-radius: 999px;
      border: 1px solid rgba(125, 211, 252, 0.35);
      background: rgba(14, 116, 144, 0.18);
      color: #bae6fd;
      padding: 2px 7px;
      font: 600 10px/1.2 system-ui, sans-serif;
      white-space: nowrap;
    }
    .cv-empty {
      padding: 28px;
      color: #64748b;
      font: italic 13px/1.5 system-ui, sans-serif;
      text-align: center;
    }
    .cv-code .k { color: #c084fc; }
    .cv-code .kn, .cv-code .kp, .cv-code .kr, .cv-code .kc { color: #c084fc; }
    .cv-code .n, .cv-code .nn, .cv-code .nb, .cv-code .nf, .cv-code .fm { color: #e2e8f0; }
    .cv-code .s, .cv-code .sa, .cv-code .sb, .cv-code .sc, .cv-code .sd, .cv-code .s1, .cv-code .s2 { color: #86efac; }
    .cv-code .mi, .cv-code .mf, .cv-code .il { color: #fbbf24; }
    .cv-code .o, .cv-code .ow { color: #fda4af; }
    .cv-code .c, .cv-code .c1, .cv-code .cm { color: #64748b; font-style: italic; }
    .cv-code .nd, .cv-code .fm { color: #7dd3fc; }
    .cv-code .na, .cv-code .bp, .cv-code .nc { color: #93c5fd; }
  `;
  el.appendChild(style);

  const shell = document.createElement("div");
  shell.className = "cv-shell";
  el.appendChild(shell);

  const rerender = () => renderCode(el, model);
  model.on("change:rendered_lines", rerender);
  model.on("change:file_name", rerender);
  model.on("change:title", rerender);
  model.on("change:status_text", rerender);
  model.on("change:highlight_lines", rerender);
  model.on("change:focus_line", rerender);
  model.on("change:selected_line", rerender);
  model.on("change:annotations_json", rerender);

  el.addEventListener("click", (event) => {
    const lineEl = event.target.closest(".cv-line");
    if (!lineEl) {
      return;
    }
    const lineNum = parseInt(lineEl.dataset.line, 10);
    if (Number.isNaN(lineNum)) {
      return;
    }
    model.set("selected_line", lineNum);
    model.save_changes();
  });

  renderCode(el, model);
}
"""


def _lexer_for(path: Path, language: str):
    if language and language != "auto":
        try:
            return get_lexer_by_name(language)
        except ClassNotFound:
            pass
    try:
        return guess_lexer_for_filename(path.name, path.read_text(encoding="utf-8", errors="replace"))
    except (ClassNotFound, OSError, UnicodeDecodeError):
        return PythonLexer()


def _highlight_lines(path: Path, source: str, language: str) -> list[str]:
    lexer = _lexer_for(path, language)
    formatter = HtmlFormatter(nowrap=True)
    html = highlight(source, lexer, formatter)
    return html.splitlines()


class CodeViewer(anywidget.AnyWidget):
    """Full-file source viewer with syntax highlighting and line annotations."""

    _esm = _ESM

    source_code = traitlets.Unicode("").tag(sync=True)
    rendered_lines = traitlets.List(traitlets.Unicode()).tag(sync=True)
    file_name = traitlets.Unicode("").tag(sync=True)
    file_path = traitlets.Unicode("").tag(sync=True)
    language = traitlets.Unicode("python").tag(sync=True)
    title = traitlets.Unicode("").tag(sync=True)
    status_text = traitlets.Unicode("").tag(sync=True)
    start_line = traitlets.Int(1).tag(sync=True)
    highlight_lines = traitlets.List(traitlets.Int()).tag(sync=True)
    focus_line = traitlets.Int(0).tag(sync=True)
    selected_line = traitlets.Int(0).tag(sync=True)
    annotations_json = traitlets.Unicode("{}").tag(sync=True)

    def _set_annotations(self, annotations: dict[int, list[str]] | None) -> None:
        payload = {
            str(line): values
            for line, values in sorted((annotations or {}).items())
            if values
        }
        self.annotations_json = json.dumps(payload, sort_keys=True)

    def show_file(
        self,
        file_path: str | Path,
        *,
        highlight_lines: list[int] | None = None,
        focus_line: int | None = None,
        title: str | None = None,
        status_text: str | None = None,
        annotations: dict[int, list[str]] | None = None,
        start_line: int | None = None,
        end_line: int | None = None,
        context: int = 5,
    ) -> None:
        """Load and display a full file, centering the active location.

        ``start_line`` / ``end_line`` remain accepted for compatibility but are
        treated only as a hint for deriving an initial focus line. The widget
        always keeps the full file loaded so the user can scroll naturally.
        """
        path = Path(file_path)
        if not path.is_file():
            self.source_code = f"# File not found: {path}"
            self.rendered_lines = [self.source_code]
            self.file_name = path.name
            self.file_path = str(path)
            self.title = title or "Missing file"
            self.status_text = status_text or "The referenced source file could not be read."
            self.highlight_lines = []
            self.focus_line = 0
            self.selected_line = 0
            self.start_line = 1
            self._set_annotations(None)
            return

        source = path.read_text(encoding="utf-8", errors="replace")
        self.source_code = source
        self.rendered_lines = _highlight_lines(path, source, self.language)
        self.file_name = path.name
        self.file_path = str(path)
        self.title = title or path.name
        self.highlight_lines = sorted(set(highlight_lines or []))
        self.start_line = start_line or 1

        derived_focus = focus_line
        if derived_focus is None and self.highlight_lines:
            derived_focus = min(self.highlight_lines)
        if derived_focus is None and start_line is not None:
            derived_focus = start_line
        if derived_focus is None and end_line is not None:
            derived_focus = max(1, end_line - context)
        self.focus_line = derived_focus or 0
        self.selected_line = self.focus_line or 0
        self.status_text = status_text or self._status_text(path, self.highlight_lines)
        self._set_annotations(annotations)

    def _status_text(self, path: Path, highlight_lines: list[int]) -> str:
        line_count = len(self.source_code.splitlines())
        if highlight_lines:
            return (
                f"{path.name} · {line_count} lines · "
                f"highlighting {len(highlight_lines)} relevant line"
                f"{'' if len(highlight_lines) == 1 else 's'}"
            )
        return f"{path.name} · {line_count} lines"

    def show_location(
        self,
        location: Location,
        *,
        title: str | None = None,
        context: int = 5,
        annotations: dict[int, list[str]] | None = None,
    ) -> None:
        """Show the file containing a location and focus its line."""
        self.show_file(
            location.file,
            highlight_lines=[location.line],
            focus_line=location.line,
            title=title,
            annotations=annotations,
            start_line=max(1, location.line - context),
        )

    def show_finding(self, finding: Finding, *, title: str | None = None, context: int = 5) -> None:
        """Show the primary file for a finding and annotate related evidence."""
        file_path = finding.location.file
        highlight_lines = [finding.location.line]
        annotations: dict[int, list[str]] = {finding.location.line: [finding.rule_id]}

        for ev in finding.evidence:
            loc = getattr(ev, "location", None)
            if loc is None or loc.file != file_path:
                continue
            highlight_lines.append(loc.line)
            label = getattr(ev, "raw_code", None) or type(ev).__name__
            annotations.setdefault(loc.line, []).append(label[:64])

        self.show_file(
            file_path,
            highlight_lines=sorted(set(highlight_lines)),
            focus_line=finding.location.line,
            title=title or f"{finding.rule_id} · {finding.title}",
            annotations=annotations,
            start_line=max(1, finding.location.line - context),
        )

    def clear(self) -> None:
        """Clear the viewer state."""
        self.source_code = ""
        self.rendered_lines = []
        self.file_name = ""
        self.file_path = ""
        self.title = ""
        self.status_text = ""
        self.start_line = 1
        self.highlight_lines = []
        self.focus_line = 0
        self.selected_line = 0
        self._set_annotations(None)
