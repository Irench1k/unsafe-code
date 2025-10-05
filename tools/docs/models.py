from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

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
    title: str | None = None
    notes: str | None = None
    http: str | None = None  # "open" | "closed" | None
    # Language hint for syntax highlighting (e.g., 'python', 'javascript')
    language: str | None = None
    parts: list[ExamplePart] = field(default_factory=list)

    # Caching/hashes
    file_hashes: dict[str, str] = field(default_factory=dict)
    fingerprint: str | None = None


@dataclass
class DirectoryIndex:
    version: str
    root: Path
    category: str | None
    namespace: str | None
    examples: dict[int, Example] = field(default_factory=dict)
    attachments: dict[str, str] = field(default_factory=dict)  # relative path -> sha256
    build_signature: str | None = None  # hash over examples + attachments
    last_readme_fingerprint: str | None = None

    def to_dict(self) -> dict:
        def ex_to_dict(ex: Example) -> dict:
            return {
                "id": ex.id,
                "kind": ex.kind,
                "title": ex.title,
                "notes": ex.notes,
                "http": ex.http,
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
                # Sort file_hashes by path key for deterministic output
                "file_hashes": {k: ex.file_hashes[k] for k in sorted(ex.file_hashes)},
                "fingerprint": ex.fingerprint,
            }

        return {
            "version": self.version,
            # Keep root path relative in the serialized index (to the directory containing index.yml)
            "root": ".",
            "category": self.category,
            "namespace": self.namespace,
            "examples": {k: ex_to_dict(v) for k, v in sorted(self.examples.items())},
            # Sort attachments for deterministic output
            "attachments": {k: self.attachments[k] for k in sorted(self.attachments)},
            "build_signature": self.build_signature,
            "last_readme_fingerprint": self.last_readme_fingerprint,
        }

    @staticmethod
    def from_dict(data: dict) -> "DirectoryIndex":
        idx = DirectoryIndex(
            version=data.get("version", "0"),
            root=Path(data.get("root", ".")),
            category=data.get("category"),
            namespace=data.get("namespace"),
        )
        exs = data.get("examples", {})
        for _, v in exs.items():
            ex = Example(
                id=int(v["id"]),
                kind=v["kind"],
                title=v.get("title"),
                notes=v.get("notes"),
                http=v.get("http"),
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
