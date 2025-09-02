from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .yaml_io import read_yaml
from .yaml_io import _normalize_notes_markdown as _normalize_markdown


@dataclass
class ReadmeSpecSection:
    title: str
    description: Optional[str]
    examples: List[int]


@dataclass
class ReadmeSpec:
    title: str
    summary: str
    description: str
    category: Optional[str]
    namespace: Optional[str]
    sections: List[ReadmeSpecSection]
    toc: bool


def load_readme_spec(path: Path) -> ReadmeSpec:
    data = read_yaml(path)

    # Validate top-level keys
    allowed_top = {"title", "summary", "description", "category", "namespace", "outline", "toc"}
    unknown_top = [k for k in data.keys() if k not in allowed_top]
    if unknown_top:
        allowed_list = ", ".join(sorted(allowed_top))
        raise ValueError(f"Unknown readme.yml key(s): {', '.join(sorted(unknown_top))}. Allowed: {allowed_list}")

    title = (data.get("title", "") or "").strip()
    summary_raw = (data.get("summary", "") or "").strip()
    description_raw = (data.get("description", "") or "").strip()
    summary = _normalize_markdown(summary_raw) if summary_raw else ""
    top_description = _normalize_markdown(description_raw) if description_raw else ""
    category = data.get("category")
    namespace = data.get("namespace")
    outline = data.get("outline", [])
    toc = bool(data.get("toc", False))

    sections: List[ReadmeSpecSection] = []
    for entry in outline:
        # Validate entry keys
        allowed_entry = {"title", "description", "examples"}
        unknown_entry = [k for k in entry.keys() if k not in allowed_entry]
        if unknown_entry:
            allowed_entry_list = ", ".join(sorted(allowed_entry))
            raise ValueError(
                f"Unknown outline entry key(s): {', '.join(sorted(unknown_entry))}. Allowed: {allowed_entry_list}"
            )
        sec_title = (entry.get("title", "") or "").strip()
        entry_description_raw = entry.get("description")
        if isinstance(entry_description_raw, str):
            entry_description = _normalize_markdown(entry_description_raw.strip())
        else:
            entry_description = entry_description_raw
        examples = entry.get("examples", [])
        sections.append(ReadmeSpecSection(title=sec_title, description=entry_description, examples=examples))

    return ReadmeSpec(
        title=title,
        summary=summary,
        description=top_description,
        category=category,
        namespace=namespace,
        sections=sections,
        toc=toc,
    )
