"""Shared widget helpers for notebook UX."""

from __future__ import annotations

from pathlib import Path


def short_name(qualname: str) -> str:
    """Return the terminal component of a qualified function name."""
    return qualname.rsplit(".", 1)[-1] if qualname else qualname


def evidence_qualname(evidence) -> str:
    """Return the function or handler qualname for any evidence fact."""
    return (
        getattr(evidence, "function_qualname", None)
        or getattr(evidence, "handler_qualname", None)
        or ""
    )


def evidence_location(evidence):
    """Return the location attached to an evidence object, if any."""
    return getattr(evidence, "location", None)


def relative_file_label(file_path: str, target_path: Path | None = None) -> str:
    """Format a file path relative to the current exercise when possible."""
    if not file_path:
        return ""
    path = Path(file_path)
    if target_path is not None:
        try:
            return str(path.relative_to(target_path))
        except ValueError:
            pass
    return path.name
