"""Markdown generation using python-markdown-generator."""

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from markdowngenerator import MarkdownGenerator

from .languages import assemble_code_from_parts
from .models import DirectoryIndex, Example


@dataclass
class TocEntry:
    id: int
    category: str
    title: str
    link: str

    def row(self, doc: MarkdownGenerator) -> List[str]:
        return [str(self.id), self.category, doc.generateHrefNotation(self.title, self.link)]


class MarkdownBuilder:
    def __init__(self, index: DirectoryIndex, title: str, intro: str, structure: List[Dict]):
        self.index = index
        self.title = title
        self.intro = intro
        self.structure = structure

    def generate(self) -> str:
        # Prevent the library from creating a physical file by providing
        # an in-memory document object.
        with MarkdownGenerator(document=io.StringIO(), enable_write=False, enable_TOC=False) as doc:
            self._render_title_and_intro(doc)
            toc_entries = self._collect_toc_entries()
            self._render_structure(doc, toc_entries)
            return "".join(doc.document_data_array)

    def _render_title_and_intro(self, doc: MarkdownGenerator) -> None:
        doc.addHeader(1, self.title)
        if self.intro:
            doc.writeTextLine(self.intro, html_escape=False)

    def _collect_toc_entries(self) -> List[TocEntry]:
        entries: List[TocEntry] = []
        for entry in self.structure:
            if entry.get("section") and entry.get("examples"):
                section_name = entry.get("section", "")
                for ex_id in entry.get("examples", []):
                    ex = self.index.examples.get(int(ex_id))
                    if ex:
                        entries.append(
                            TocEntry(
                                id=ex.id,
                                category=section_name,
                                title=(ex.title or f"Example {ex.id}"),
                                link=self._get_code_link(ex),
                            )
                        )
        return entries

    def _add_table_of_contents(self, doc: MarkdownGenerator, entries: List[TocEntry]) -> None:
        doc.addHeader(2, "Table of Contents")
        rows = [e.row(doc) for e in entries]
        doc.addTable(header_names=["Index", "Category", "Example"], row_elements=rows, alignment="center", html_escape=False)

    def _render_structure(self, doc: MarkdownGenerator, toc_entries: List[TocEntry]) -> None:
        for entry in self.structure:
            if self._is_toc_marker(entry):
                self._add_table_of_contents(doc, toc_entries)
                continue
            section_title = entry.get("section", "")
            if section_title:
                doc.addHeader(2, section_title)
            description = entry.get("description", "")
            if description:
                doc.writeTextLine(description, html_escape=False)
            for ex_id in entry.get("examples", []):
                ex = self.index.examples.get(int(ex_id))
                if ex:
                    self._add_example_section(doc, ex)

    @staticmethod
    def _is_toc_marker(entry: Dict) -> bool:
        return bool(entry.get("table-of-contents") or entry.get("table_of_contents"))

    def _add_example_section(self, doc: MarkdownGenerator, example: Example) -> None:
        # Header, add colon only if title present
        if example.title:
            doc.addHeader(3, f"Example {example.id}: {example.title}")
        else:
            doc.addHeader(3, f"Example {example.id}")

        if example.notes:
            doc.writeTextLine(example.notes, html_escape=False)

        # Code block: content assembled externally, use language from index
        if example.parts:
            code_content = assemble_code_from_parts(example.parts)
            if code_content:
                doc.addCodeBlock(code_content, syntax=example.language or "")

        # HTTP request (details/summary)
        self._add_http_request(doc, example)

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
            is_open = (example.request_details or "").lower() == "open"

            if is_open:
                # Library lacks 'open'; write tags manually
                doc.writeTextLine("<details open>", html_escape=False)
                doc.writeTextLine("<summary><b>See HTTP Request</b></summary>", html_escape=False)
                doc.writeTextLine()
                doc.addCodeBlock(http_content, syntax="http")
                doc.writeTextLine("</details>", html_escape=False)
                # Critical: extra blank line after closing details
                doc.writeTextLine()
            else:
                doc.insertDetailsAndSummary(summary_name="<b>See HTTP Request</b>", escape_html=False)
                doc.addCodeBlock(http_content, syntax="http")
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


def generate_readme(index: DirectoryIndex, title: str, intro: str, structure: List[Dict]) -> str:
    """Public API for README generation."""
    return MarkdownBuilder(index, title, intro, structure).generate()
