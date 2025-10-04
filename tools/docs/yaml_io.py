from pathlib import Path
from typing import Any, Dict

import textwrap

import yaml


def read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class _FoldedStr(str):
    """Marker subclass for YAML folded scalar (>) emission."""


def _represent_folded_str(dumper: yaml.Dumper, data: _FoldedStr):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style=">")


# Register for both the default Dumper and SafeDumper
yaml.add_representer(_FoldedStr, _represent_folded_str)
yaml.add_representer(_FoldedStr, _represent_folded_str, Dumper=yaml.SafeDumper)


def _deep_convert_notes_to_folded(value: Any) -> Any:
    if isinstance(value, dict):
        new = {}
        for k, v in value.items():
            if k == "notes" and isinstance(v, str):
                new[k] = _FoldedStr(v)
            else:
                new[k] = _deep_convert_notes_to_folded(v)
        return new
    if isinstance(value, list):
        return [_deep_convert_notes_to_folded(v) for v in value]
    return value


def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    # Convert notes fields to folded scalars for nice YAML formatting
    data = _deep_convert_notes_to_folded(data)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, width=88)


# ----- Annotation YAML parsing (centralized PyYAML usage) -----

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


def _normalize_notes_markdown(text: str) -> str:
    """Normalize markdown notes:

    - Collapse intra-paragraph line breaks to single spaces
    - Collapse multiple blank lines to a single blank line
    - Preserve fenced code blocks verbatim (``` ... ```)
    - Preserve list items (unordered: -, *; ordered: 1., 2., etc.)
    """
    if not text:
        return ""

    import re

    lines = text.splitlines()
    out_blocks: list[str] = []
    in_code = False
    para_acc: list[str] = []

    # Pattern to match list items: unordered (- or *) or ordered (digit(s) followed by .)
    list_item_pattern = re.compile(r"^(\s*)([-*]|\d+\.)\s+")

    def is_list_item(line: str) -> bool:
        """Check if a line is a list item."""
        return bool(list_item_pattern.match(line))

    def flush_para():
        nonlocal para_acc
        if para_acc:
            # Join with a single space
            joined = " ".join(s.strip() for s in para_acc if s is not None)
            out_blocks.append(joined)
            para_acc = []

    i = 0
    while i < len(lines):
        ln = lines[i]
        stripped = ln.strip()
        if stripped.startswith("```"):
            flush_para()
            # Collect entire fenced block
            code_block = [ln]
            i += 1
            while i < len(lines):
                code_block.append(lines[i])
                if lines[i].strip().startswith("```"):
                    i += 1
                    break
                i += 1
            out_blocks.append("\n".join(code_block))
            continue
        if stripped.startswith("#"):
            # Treat ATX headers as their own blocks; do not merge with following lines
            flush_para()
            out_blocks.append(stripped)
            # Ensure a blank line after header for readability
            out_blocks.append("")
            i += 1
            continue
        if is_list_item(ln):
            # List items are treated as their own blocks, not joined with surrounding text
            flush_para()
            out_blocks.append(stripped)
            i += 1
            continue
        if stripped == "":
            # Blank line separates paragraphs
            flush_para()
            # Ensure at most a single blank line between blocks
            if out_blocks and out_blocks[-1] != "":
                out_blocks.append("")
            elif not out_blocks:
                # avoid leading blank blocks
                pass
            i += 1
            continue
        # Accumulate paragraph lines
        para_acc.append(ln)
        i += 1

    flush_para()
    # Remove trailing blank blocks
    while out_blocks and out_blocks[-1] == "":
        out_blocks.pop()

    # Re-join: ensure single blank line between blocks
    result: list[str] = []
    for b in out_blocks:
        if b == "":
            if result and result[-1] != "":
                result.append("")
        else:
            result.append(b)
    return "\n".join(result)


def parse_annotation_metadata(yaml_content: str) -> Dict[str, Any]:
    """Parse YAML metadata for fenced @unsafe annotations.

    Strict rules:
    - Required: id (int)
    - Optional: title (str), notes (str markdown), http ("open"|"closed"), part (int >= 1)
    - Unknown keys are errors (no aliases accepted)

    Performs type casting and trims string fields to normalize input.
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

    # Enforce canonical keys only
    allowed_keys = {"id", "title", "notes", "http", "part"}
    unknown = [k for k in data.keys() if k not in allowed_keys]
    if unknown:
        allowed_list = ", ".join(sorted(allowed_keys))
        raise ValueError(f"Unknown annotation key(s): {', '.join(sorted(unknown))}. Allowed: {allowed_list}")

    def _s(v: Any) -> str:
        return str(v).strip()

    def _normalize_title(text: str) -> str:
        # Collapse all whitespace (including newlines) to single spaces
        return " ".join(text.split())

    result: Dict[str, Any] = {
        'id': int(data['id']),
    }
    if 'title' in data and data['title'] is not None:
        result['title'] = _normalize_title(_s(data['title']))
    if 'notes' in data and data['notes'] is not None:
        # Normalize multiline markdown notes for clean YAML and stable rendering
        normalized = _normalize_notes_markdown(_s(data['notes']))
        result['notes'] = normalized
    # HTTP details: 'open' or 'closed' (default closed). Use canonical key 'http'.
    if 'http' in data and data['http'] is not None:
        http_val = _s(data['http']).lower()
        if http_val not in ("open", "closed"):
            raise ValueError("Invalid value for 'http'. Allowed: 'open' or 'closed'")
        result['http'] = http_val
    if 'part' in data and data['part'] is not None:
        part_int = int(data['part'])
        if part_int < 1:
            raise ValueError("'part' must be >= 1")
        result['part'] = part_int

    return result
