"""Markdown generation using python-markdown-generator."""

import io
from dataclasses import dataclass

from markdowngenerator import MarkdownGenerator

from .languages import assemble_code_from_parts
from .models import DirectoryIndex, Example


@dataclass
class TocEntry:
    id: int
    category: str
    section_label: str
    section_link: str
    file_label: str
    file_link: str

    def row(self, doc: MarkdownGenerator) -> list[str]:
        return [
            self.category,
            doc.generateHrefNotation(self.section_label, self.section_link),
            doc.generateHrefNotation(self.file_label, self.file_link),
        ]


class MarkdownBuilder:
    def __init__(self, index: DirectoryIndex, title: str, summary: str, description: str, sections: list[dict], toc: bool):
        self.index = index
        self.title = title
        self.summary = summary
        self.description = description
        self.sections = sections
        self.toc = toc

    def generate(self) -> str:
        # Prevent the library from creating a physical file by providing
        # an in-memory document object.
        with MarkdownGenerator(document=io.StringIO(), enable_write=False, enable_TOC=False) as doc:
            self._render_title_and_intro(doc)
            toc_entries = self._collect_toc_entries()
            if self.toc and toc_entries:
                self._add_table_of_contents(doc, toc_entries)
            self._render_structure(doc, toc_entries)
            raw = "".join(doc.document_data_array)
            return self._cleanup_markdown(raw)

    def _render_title_and_intro(self, doc: MarkdownGenerator) -> None:
        doc.addHeader(1, self.title)
        doc.writeTextLine()  # Blank line after title
        if self.summary:
            doc.writeTextLine(self.summary, html_escape=False)
            doc.writeTextLine()  # Blank line after summary
        if self.description:
            doc.writeTextLine(self.description, html_escape=False)

    def _collect_toc_entries(self) -> list[TocEntry]:
        entries: list[TocEntry] = []
        for entry in self.sections:
            section_name = entry.get("title", "")
            for ex_id in entry.get("examples", []):
                ex = self.index.examples.get(int(ex_id))
                if ex:
                    # Section link anchors are stable via explicit ids per example
                    section_label = (
                        f"Example {ex.id}: {ex.title}" if ex.title else f"Example {ex.id}"
                    )
                    section_link = f"#ex-{ex.id}"
                    # File label and link
                    file_label = self._get_file_label(ex)
                    file_link = self._get_code_link(ex)
                    entries.append(
                        TocEntry(
                            id=ex.id,
                            category=section_name,
                            section_label=section_label,
                            section_link=section_link,
                            file_label=file_label,
                            file_link=file_link,
                        )
                    )
        return entries

    def _add_table_of_contents(self, doc: MarkdownGenerator, entries: list[TocEntry]) -> None:
        doc.addHeader(2, "Table of Contents")
        rows = [e.row(doc) for e in entries]
        doc.addTable(
            header_names=["Category", "Example", "File"],
            row_elements=rows,
            alignment="center",
            html_escape=False,
        )

    def _render_structure(self, doc: MarkdownGenerator, toc_entries: list[TocEntry]) -> None:
        for entry in self.sections:
            section_title = entry.get("title", "")
            if section_title:
                doc.addHeader(2, section_title)
                doc.writeTextLine()  # Blank line after section header
            description = entry.get("description", "")
            if description:
                doc.writeTextLine(description, html_escape=False)
                doc.writeTextLine()  # Blank line after section description
            for ex_id in entry.get("examples", []):
                ex = self.index.examples.get(int(ex_id))
                if ex:
                    self._add_example_section(doc, ex)

    # No special ToC marker: handled globally via spec.toc

    def _add_example_section(self, doc: MarkdownGenerator, example: Example) -> None:
        # Header with inline anchor for intra-document links
        if example.title:
            doc.writeTextLine(f"### Example {example.id}: {example.title} <a id=\"ex-{example.id}\"></a>", html_escape=False)
        else:
            doc.writeTextLine(f"### Example {example.id} <a id=\"ex-{example.id}\"></a>", html_escape=False)
        doc.writeTextLine()  # Blank line after example header

        if example.notes:
            doc.writeTextLine(example.notes, html_escape=False)

        # Code block: content assembled externally, use language from index
        if example.parts:
            code_content = assemble_code_from_parts(example.parts)
            if code_content:
                doc.addCodeBlock(code_content, syntax=example.language or "")

        # HTTP request (details/summary)
        self._add_http_request(doc, example)

        # Add source code link
        self._add_source_code_link(doc, example)

        # Image if exists
        self._add_image(doc, example)

    def _add_http_request(self, doc: MarkdownGenerator, example: Example) -> None:
        """Insert collapsible HTTP request details when available.

        Ensures a blank line after the details block so that subsequent Markdown
        (e.g., images) is parsed correctly and not captured by the HTML block.
        """
        http_file = self.index.root / "http" / f"exploit-{example.id}.http"
        if not http_file.exists():
            return
        try:
            http_content = http_file.read_text(encoding="utf-8").strip()
            is_open = (example.http or "").lower() == "open"

            if is_open:
                # Library lacks 'open'; write tags manually
                doc.writeTextLine("<details open>", html_escape=False)
                doc.writeTextLine("<summary><b>See HTTP Request</b></summary>", html_escape=False)
                doc.writeTextLine()
                doc.addCodeBlock(http_content, syntax="shell")
                doc.writeTextLine("</details>", html_escape=False)
                # Critical: extra blank line after closing details
                doc.writeTextLine()
            else:
                doc.insertDetailsAndSummary(summary_name="<b>See HTTP Request</b>", escape_html=False)
                doc.addCodeBlock(http_content, syntax="shell")
                doc.endDetailsAndSummary()
                # Critical: extra blank line after closing details
                doc.writeTextLine()
        except Exception:
            # Silently skip request section on read errors
            pass

    def _add_image(self, doc: MarkdownGenerator, example: Example) -> None:
        """Add an example image if present (ensures proper separation)."""
        image_file = self.index.root / "images" / f"image-{example.id}.png"
        if not image_file.exists():
            return
        relative_path = f"images/image-{example.id}.png"
        doc.writeTextLine(doc.generateImageHrefNotation(relative_path, "alt text"), html_escape=False)

    def _add_source_code_link(self, doc: MarkdownGenerator, example: Example) -> None:
        """Add a link to the source code file after the example."""
        if not example.parts:
            return
        
        file_label = self._get_file_label(example)
        code_link = self._get_code_link(example)
        
        if file_label and code_link:
            doc.writeTextLine(f"See the code here: [{file_label}]({code_link})", html_escape=False)
            doc.writeTextLine()  # Blank line after source code link

    def _get_code_link(self, example: Example) -> str:
        if not example.parts:
            return ""
        # Prefer the first part (parts are built in order)
        first_part = min(example.parts, key=lambda p: p.part)
        relative_path = first_part.file_path.relative_to(self.index.root).as_posix()
        if first_part.code_start_line and first_part.code_end_line and first_part.code_start_line != first_part.code_end_line:
            return f"{relative_path}#L{first_part.code_start_line}-L{first_part.code_end_line}"
        elif first_part.code_start_line:
            return f"{relative_path}#L{first_part.code_start_line}"
        else:
            return relative_path

    def _get_file_label(self, example: Example) -> str:
        if not example.parts:
            return ""
        first_part = min(example.parts, key=lambda p: p.part)
        return first_part.file_path.relative_to(self.index.root).as_posix()


    @staticmethod
    def _cleanup_markdown(md: str) -> str:
        """Remove trailing spaces and collapse excessive blank lines outside code fences."""
        lines = md.splitlines()
        out: list[str] = []
        in_code = False
        fence = "```"
        blank_streak = 0
        for ln in lines:
            stripped = ln.rstrip("\n\r")
            if stripped.strip().startswith(fence):
                # Preserve fence lines verbatim and toggle state
                in_code = not in_code
                out.append(stripped.rstrip())
                blank_streak = 0
                continue
            if in_code:
                out.append(ln)
                blank_streak = 0 if ln.strip() else blank_streak + 1
                continue
            # Outside code: strip trailing spaces
            trimmed = stripped.rstrip()
            if trimmed == "":
                blank_streak += 1
                if blank_streak <= 1:
                    out.append("")
            else:
                blank_streak = 0
                out.append(trimmed)
        return "\n".join(out) + ("\n" if md.endswith("\n") else "")


def generate_readme(index: DirectoryIndex, title: str, summary: str, description: str, sections: list[dict], toc: bool) -> str:
    """Public API for README generation."""
    return MarkdownBuilder(index, title, summary, description, sections, toc).generate()