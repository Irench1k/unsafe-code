from pathlib import Path
from typing import Any, Dict

import yaml


def read_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


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


def parse_annotation_metadata(yaml_content: str) -> Dict[str, Any]:
    """Parse YAML metadata for @unsafe annotations.

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

    def _s(v: Any) -> str:
        return str(v).strip()

    result: Dict[str, Any] = {
        'id': int(data['id']),
    }
    if 'title' in data and data['title'] is not None:
        result['title'] = _s(data['title'])
    if 'notes' in data and data['notes'] is not None:
        # Preserve multi-line notes but trim trailing/leading whitespace
        result['notes'] = _s(data['notes'])
    # Normalize request-details variations
    if 'request-details' in data and data['request-details'] is not None:
        result['request-details'] = _s(data['request-details'])
    elif 'request_details' in data and data['request_details'] is not None:
        result['request-details'] = _s(data['request_details'])
    if 'part' in data and data['part'] is not None:
        result['part'] = int(data['part'])

    return result
