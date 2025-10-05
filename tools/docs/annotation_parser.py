"""Annotation parser for @unsafe markers using strict YAML parsing."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from .models import AnnotationKind
from .yaml_io import parse_annotation_metadata


@dataclass
class RawAnnotation:
    """Raw annotation data before processing."""
    file_path: Path
    start_line: int  # 1-based line where @unsafe appears
    end_line: int    # 1-based line where @/unsafe appears
    kind: AnnotationKind
    metadata: dict[str, Any]


def find_annotation_boundaries(line: str) -> tuple[str, int] | None:
    """Find @unsafe marker in a line and return (kind, indentation)."""
    stripped = line.lstrip()
    indent = len(line) - len(stripped)
    match = re.search(r'@unsafe\[(function|block)\]', stripped)
    if match:
        return match.group(1), indent
    return None


def find_closing_marker(lines: list[str], start_idx: int, target_indent: int) -> int | None:
    """Find the matching @/unsafe marker at the same indentation level."""
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == target_indent and '@/unsafe' in stripped:
            return i
    return None


def extract_yaml_content(lines: list[str], start_idx: int, end_idx: int) -> str:
    """Extract YAML content between @unsafe and @/unsafe markers.

    - Strips single-line comment markers while preserving spaces after them
    - Dedents by the smallest common leading whitespace across non-empty lines
    """
    cleaned_lines: list[str] = []
    for i in range(start_idx + 1, end_idx):
        cleaned_lines.append(remove_comment_prefix(lines[i]))

    # Compute minimal leading spaces among non-empty lines
    non_empty = [ln for ln in cleaned_lines if ln.strip()]
    if not non_empty:
        return ""
    min_leading = min(len(ln) - len(ln.lstrip(" ")) for ln in non_empty)
    dedented = [ln[min_leading:] if len(ln) >= min_leading else ln for ln in cleaned_lines]
    return "\n".join(dedented)


def remove_comment_prefix(line: str) -> str:
    """Remove a single-line comment prefix, preserving all following spaces.

    We intentionally do not strip spaces after the comment token so YAML
    indentation remains intact. For block-style comments, we strip only the
    marker (`/*`, `*`, `*/`) and retain the rest of the line verbatim.
    """
    patterns = [
        r'^(\s*)#(.*)',       # Python `# ...`
        r'^(\s*)//(.*)',      # JS/TS `// ...`
        r'^(\s*)/\*(.*)',    # Block start `/* ...`
        r'^(\s*)\*(.*)',     # Block middle `* ...`
        r'^(\s*)\*/(.*)',    # Block end `*/ ...`
    ]
    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            return match.group(1) + match.group(2)
    return line


# parse_annotation_metadata is now provided by tools.docs.yaml_io


def find_block_end_marker(lines: list[str], start_line: int) -> int | None:
    """Find @/unsafe[block] marker for block annotations (1-based)."""
    for i in range(start_line - 1, len(lines)):
        if '@/unsafe[block]' in lines[i]:
            return i + 1
    return None


def parse_file_annotations(file_path: Path) -> list[RawAnnotation]:
    """Parse all @unsafe annotations from a single file."""
    try:
        with open(file_path, encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        raise ValueError(f"Cannot read file {file_path}: {e}") from e

    lines = [line.rstrip('\n\r') for line in lines]
    annotations: list[RawAnnotation] = []
    i = 0
    while i < len(lines):
        boundary = find_annotation_boundaries(lines[i])
        if not boundary:
            i += 1
            continue

        kind, indent = boundary
        end_idx = find_closing_marker(lines, i, indent)
        if end_idx is None:
            raise ValueError(
                f"Missing @/unsafe closing marker for annotation at {file_path}:{i+1}"
            )

        yaml_content = extract_yaml_content(lines, i, end_idx)
        metadata = parse_annotation_metadata(yaml_content)

        annotations.append(
            RawAnnotation(
                file_path=file_path,
                start_line=i + 1,
                end_line=end_idx + 1,
                kind=cast(AnnotationKind, kind),
                metadata=metadata,
            )
        )
        i = end_idx + 1

    return annotations


def discover_annotations(files: list[Path]) -> list[RawAnnotation]:
    """Discover all annotations across multiple files.

    Strict mode: any parsing error aborts with a clear exception.
    """
    all_annotations: list[RawAnnotation] = []
    for file_path in files:
        all_annotations.extend(parse_file_annotations(file_path))
    return all_annotations
