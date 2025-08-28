"""Markdown generation using python-markdown-generator."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from markdowngenerator import MarkdownGenerator

from .languages import get_language_name_for_file
from .models import DirectoryIndex, Example


def generate_readme(
    index: DirectoryIndex, 
    title: str, 
    intro: str, 
    structure: List[Dict]
) -> str:
    """Generate README content using MarkdownGenerator."""
    
    with MarkdownGenerator(filename=None, enable_write=False, enable_TOC=False) as doc:
        # Title
        doc.addHeader(1, title)
        
        # Introduction
        if intro:
            doc.writeTextLine()
            doc.writeTextLine(intro.strip())
            doc.writeTextLine()
        
        # Process structure
        toc_entries = _collect_toc_entries(index, structure)
        
        for entry in structure:
            if entry.get("table-of-contents") or entry.get("table_of_contents"):
                _add_table_of_contents(doc, toc_entries)
                continue
            
            # Section header
            section_title = entry.get("section", "")
            if section_title:
                doc.addHeader(2, section_title)
                
            # Section description
            description = entry.get("description", "")
            if description:
                doc.writeTextLine()
                doc.writeTextLine(description.strip())
                doc.writeTextLine()
            
            # Examples in this section
            for ex_id in entry.get("examples", []):
                ex = index.examples.get(int(ex_id))
                if ex:
                    _add_example_section(doc, ex, index)
        
        # Get the generated content
        return '\n'.join(doc.document_data_array)


def _collect_toc_entries(index: DirectoryIndex, structure: List[Dict]) -> List[Dict]:
    """Collect table of contents entries based on structure."""
    toc_entries = []
    
    for entry in structure:
        if entry.get("section") and entry.get("examples"):
            section_name = entry.get("section", "")
            for ex_id in entry.get("examples", []):
                ex = index.examples.get(int(ex_id))
                if ex:
                    link = _get_code_link(ex, index.root)
                    toc_entries.append({
                        'id': ex.id,
                        'category': section_name,
                        'title': ex.title or f'Example {ex.id}',
                        'link': link
                    })
    
    return toc_entries


def _add_table_of_contents(doc: MarkdownGenerator, entries: List[Dict]) -> None:
    """Add table of contents to the document."""
    doc.addHeader(2, "Table of Contents")
    
    # Create table manually for better formatting
    doc.writeTextLine()
    doc.writeTextLine("| Index | Category | Example |", html_escape=False)
    doc.writeTextLine("| ----- | -------- | ------- |", html_escape=False)
    
    for entry in entries:
        link_text = doc.generateHrefNotation(entry['title'], entry['link'])
        row = f"| {entry['id']} | {entry['category']} | {link_text} |"
        doc.writeTextLine(row, html_escape=False)
    
    doc.writeTextLine()


def _add_example_section(doc: MarkdownGenerator, example: Example, index: DirectoryIndex) -> None:
    """Add a complete example section to the document."""
    # Example header
    doc.addHeader(3, f"Example {example.id}: {example.title or ''}")
    
    # Notes
    if example.notes:
        doc.writeTextLine()
        doc.writeTextLine(example.notes.strip())
        doc.writeTextLine()
    
    # Code block
    _add_code_block(doc, example)
    
    # HTTP request
    _add_http_request(doc, example, index.root)
    
    # Image
    _add_image(doc, example, index.root)


def _add_code_block(doc: MarkdownGenerator, example: Example) -> None:
    """Add code block for an example."""
    if not example.parts:
        return
        
    # Sort parts by part number
    parts = sorted(example.parts, key=lambda p: p.part)
    
    # Determine language from first part
    first_part = parts[0]
    language = get_language_name_for_file(first_part.file_path)
    
    # Collect code from all parts
    code_lines = []
    
    for i, part in enumerate(parts):
        try:
            with open(part.file_path, 'r', encoding='utf-8') as f:
                file_lines = f.readlines()
            
            # Extract the specified lines (convert to 0-based indexing)
            start_idx = max(0, part.code_start_line - 1)
            end_idx = min(len(file_lines), part.code_end_line)
            
            part_lines = [line.rstrip() for line in file_lines[start_idx:end_idx]]
            code_lines.extend(part_lines)
            
            # Add separator between parts (but not after the last part)
            if i < len(parts) - 1:
                code_lines.append('')  # Empty line between parts
                
        except Exception:
            # If we can't read the file, skip this part
            continue
    
    if code_lines:
        code_content = '\n'.join(code_lines)
        doc.addCodeBlock(code_content, syntax=language)


def _add_http_request(doc: MarkdownGenerator, example: Example, root: Path) -> None:
    """Add HTTP request section if file exists."""
    http_file = root / "http" / f"exploit-{example.id}.http"
    
    if not http_file.exists():
        return
    
    try:
        http_content = http_file.read_text(encoding='utf-8').strip()
        
        # Determine if details should be open
        is_open = (example.request_details or "").lower() == "open"
        
        if is_open:
            doc.writeTextLine('<details open>', html_escape=False)
        else:
            doc.writeTextLine('<details>', html_escape=False)
            
        doc.writeTextLine('  <summary><b>See HTTP Request</b></summary>', html_escape=False)
        doc.writeTextLine()
        
        doc.addCodeBlock(http_content, syntax='http')
        
        doc.writeTextLine('</details>', html_escape=False)
        
    except Exception:
        # If we can't read the HTTP file, skip it
        pass


def _add_image(doc: MarkdownGenerator, example: Example, root: Path) -> None:
    """Add image section if file exists."""
    image_file = root / "images" / f"image-{example.id}.png"
    
    if image_file.exists():
        relative_path = f"images/image-{example.id}.png"
        doc.writeTextLine(doc.generateImageHrefNotation(relative_path, "alt text"), html_escape=False)


def _get_code_link(example: Example, root: Path) -> str:
    """Generate code link for table of contents."""
    if not example.parts:
        return ""
    
    # Use first part for the link
    first_part = sorted(example.parts, key=lambda p: p.part)[0]
    relative_path = first_part.file_path.relative_to(root).as_posix()
    
    if (first_part.code_start_line and 
        first_part.code_end_line and 
        first_part.code_start_line != first_part.code_end_line):
        return f"{relative_path}#L{first_part.code_start_line}-L{first_part.code_end_line}"
    elif first_part.code_start_line:
        return f"{relative_path}#L{first_part.code_start_line}"
    else:
        return relative_path

