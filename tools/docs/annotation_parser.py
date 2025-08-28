"""Annotation parser for @unsafe markers using strict YAML parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any

import yaml

from .models import AnnotationKind


@dataclass
class RawAnnotation:
    """Raw annotation data before processing."""
    file_path: Path
    start_line: int  # 1-based line where @unsafe appears
    end_line: int    # 1-based line where @/unsafe appears
    kind: AnnotationKind
    metadata: Dict[str, Any]


def find_annotation_boundaries(line: str) -> tuple[str, int] | None:
    """Find @unsafe marker in a line and return (kind, indentation)."""
    stripped = line.lstrip()
    indent = len(line) - len(stripped)
    match = re.search(r'@unsafe\[(function|block)\]', stripped)
    if match:
        return match.group(1), indent
    return None


def find_closing_marker(lines: List[str], start_idx: int, target_indent: int) -> int | None:
    """Find the matching @/unsafe marker at the same indentation level."""
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == target_indent and '@/unsafe' in stripped:
            return i
    return None


def extract_yaml_content(lines: List[str], start_idx: int, end_idx: int) -> str:
    """Extract YAML content between @unsafe and @/unsafe markers.

    - Strips single-line comment markers while preserving spaces after them
    - Dedents by the smallest common leading whitespace across non-empty lines
    """
    cleaned_lines: List[str] = []
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


def _format_yaml_error(yaml_content: str, err: yaml.YAMLError) -> str:
    """Return a readable error message with a code frame for YAML errors."""
    header = "Invalid YAML in annotation:"
    body = str(err).strip()
    frame_lines = []
    try:
        mark = getattr(err, 'problem_mark', None)
        if mark is not None and hasattr(mark, 'line'):
            err_line = mark.line  # 0-based within yaml_content
        else:
            err_line = None
    except Exception:
        err_line = None

    src_lines = yaml_content.splitlines()
    for i, ln in enumerate(src_lines, start=1):
        prefix = '>' if (err_line is not None and i == err_line + 1) else ' '
        frame_lines.append(f"{prefix} {i:03d}: {ln}")
    frame = "\n".join(frame_lines)
    return f"{header}\n{body}\n\n{frame}"


def parse_annotation_metadata(yaml_content: str) -> Dict[str, Any]:
    """Parse YAML metadata from annotation content using PyYAML only.

    Raises a ValueError with a precise message on parsing or validation errors.
    """
    if not yaml_content.strip():
        raise ValueError("Empty annotation metadata; 'id' is required")

    try:
        data = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError as e:
        raise ValueError(_format_yaml_error(yaml_content, e)) from e

    if 'id' not in data:
        raise ValueError("Missing required 'id' field in annotation")

    result: Dict[str, Any] = {
        'id': int(data['id']),
    }
    if 'title' in data:
        result['title'] = str(data['title'])
    if 'notes' in data:
        # Preserve multi-line notes
        result['notes'] = str(data['notes']).rstrip()
    # Normalize request-details variations
    if 'request-details' in data:
        result['request-details'] = str(data['request-details'])
    elif 'request_details' in data:
        result['request-details'] = str(data['request_details'])
    if 'part' in data:
        result['part'] = int(data['part'])

    return result


def find_block_end_marker(lines: List[str], start_line: int) -> int | None:
    """Find @/unsafe[block] marker for block annotations (1-based)."""
    for i in range(start_line - 1, len(lines)):
        if '@/unsafe[block]' in lines[i]:
            return i + 1
    return None


def parse_file_annotations(file_path: Path) -> List[RawAnnotation]:
    """Parse all @unsafe annotations from a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        raise ValueError(f"Cannot read file {file_path}: {e}")

    lines = [line.rstrip('\n\r') for line in lines]
    annotations: List[RawAnnotation] = []
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
                kind=kind,
                metadata=metadata,
            )
        )
        i = end_idx + 1

    return annotations


def discover_annotations(files: List[Path]) -> List[RawAnnotation]:
    """Discover all annotations across multiple files."""
    all_annotations: List[RawAnnotation] = []
    for file_path in files:
        try:
            all_annotations.extend(parse_file_annotations(file_path))
        except Exception as e:
            print(f"Warning: Failed to parse annotations in {file_path}: {e}")
    return all_annotations
