"""Backend interface that all code analysis backends must implement.

Each backend (AST, Joern, CodeQL) extracts raw facts from source code.
The detection engine consumes only the normalized facts, never the backend
directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..models import (
    BeforeRequestFact,
    CallEdge,
    DictMergeFact,
    InputAccessFact,
    RouteFact,
)


@dataclass
class ExtractionResult:
    """All facts extracted from a codebase by a backend."""

    routes: list[RouteFact]
    input_accesses: list[InputAccessFact]
    call_edges: list[CallEdge]
    before_requests: list[BeforeRequestFact]
    dict_merges: list[DictMergeFact]

    def __post_init__(self) -> None:
        seen: set[tuple] = set()
        unique: list[InputAccessFact] = []
        for a in self.input_accesses:
            # Keep distinct sites even when the same function reads the same
            # key/source more than once. CONF-001 needs those repeated sites to
            # compare source-selection policies such as args->form vs form->args.
            key = (
                a.function_qualname,
                a.location.file,
                a.location.line,
                a.location.col,
                a.key_literal,
                a.source.value,
                a.accessor.value,
                a.raw_code,
                tuple(a.notes),
            )
            if key not in seen:
                seen.add(key)
                unique.append(a)
        self.input_accesses = unique

    @property
    def files_analyzed(self) -> set[str]:
        files: set[str] = set()
        for r in self.routes:
            files.add(r.location.file)
        for ia in self.input_accesses:
            files.add(ia.location.file)
        return files


class Backend(Protocol):
    """Protocol for code analysis backends."""

    name: str

    def extract(self, target: Path) -> ExtractionResult:
        """Analyze source code at `target` and return normalized facts."""
        ...
