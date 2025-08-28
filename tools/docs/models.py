from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional


AnnotationKind = Literal["function", "block"]


@dataclass
class ExamplePart:
    id: int
    part: int
    file_path: Path
    code_start_line: int
    code_end_line: int


@dataclass
class Example:
    id: int
    kind: AnnotationKind
    title: Optional[str] = None
    notes: Optional[str] = None
    request_details: Optional[str] = None  # "open" | "closed" | None
    # Language hint for syntax highlighting (e.g., 'python', 'javascript')
    language: Optional[str] = None
    parts: List[ExamplePart] = field(default_factory=list)

    # Caching/hashes
    file_hashes: Dict[str, str] = field(default_factory=dict)
    fingerprint: Optional[str] = None


@dataclass
class DirectoryIndex:
    version: str
    root: Path
    category: Optional[str]
    id_prefix: Optional[str]
    examples: Dict[int, Example] = field(default_factory=dict)
    attachments: Dict[str, str] = field(default_factory=dict)  # relative path -> sha256
    build_signature: Optional[str] = None  # hash over examples + attachments
    last_readme_fingerprint: Optional[str] = None

    def to_dict(self) -> dict:
        def ex_to_dict(ex: Example) -> dict:
            return {
                "id": ex.id,
                "kind": ex.kind,
                "title": ex.title,
                "notes": ex.notes,
                "request_details": ex.request_details,
                "language": ex.language,
                "parts": [
                    {
                        "part": p.part,
                        # Store file paths relative to the index root to avoid leaking absolute paths
                        "file": str(Path(p.file_path).relative_to(self.root).as_posix()),
                        "code_start_line": p.code_start_line,
                        "code_end_line": p.code_end_line,
                    }
                    for p in sorted(ex.parts, key=lambda pp: pp.part)
                ],
                "file_hashes": ex.file_hashes,
                "fingerprint": ex.fingerprint,
            }

        return {
            "version": self.version,
            # Keep root path relative in the serialized index (to the directory containing index.yml)
            "root": ".",
            "category": self.category,
            "id_prefix": self.id_prefix,
            "examples": {k: ex_to_dict(v) for k, v in sorted(self.examples.items())},
            "attachments": self.attachments,
            "build_signature": self.build_signature,
            "last_readme_fingerprint": self.last_readme_fingerprint,
        }

    @staticmethod
    def from_dict(data: dict) -> "DirectoryIndex":
        idx = DirectoryIndex(
            version=data.get("version", "0"),
            root=Path(data.get("root", ".")),
            category=data.get("category"),
            id_prefix=data.get("id_prefix"),
        )
        exs = data.get("examples", {})
        for _, v in exs.items():
            ex = Example(
                id=int(v["id"]),
                kind=v["kind"],
                title=v.get("title"),
                notes=v.get("notes"),
                request_details=v.get("request_details"),
                language=v.get("language"),
            )
            for p in v.get("parts", []):
                ex.parts.append(
                    ExamplePart(
                        id=ex.id,
                        part=int(p["part"]),
                        file_path=Path(p["file"]),
                        code_start_line=int(p["code_start_line"]),
                        code_end_line=int(p["code_end_line"]),
                    )
                )
            ex.file_hashes = v.get("file_hashes", {})
            ex.fingerprint = v.get("fingerprint")
            idx.examples[ex.id] = ex
        idx.attachments = data.get("attachments", {})
        idx.build_signature = data.get("build_signature")
        idx.last_readme_fingerprint = data.get("last_readme_fingerprint")
        return idx
