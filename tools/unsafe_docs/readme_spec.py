from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .yaml_io import read_yaml


@dataclass
class ReadmeSpecExample:
    id: int


@dataclass
class ReadmeSpecSection:
    title: str
    description: Optional[str]
    examples: List[int]


@dataclass
class ReadmeSpec:
    title: str
    intro: str
    category: Optional[str]
    id_prefix: Optional[str]
    sections: List[ReadmeSpecSection]
    table_of_contents: bool


def load_readme_spec(path: Path) -> ReadmeSpec:
    data = read_yaml(path)
    title = data.get("title", "")
    intro = data.get("intro", "")
    category = data.get("category")
    id_prefix = data.get("id-prefix") or data.get("id_prefix")
    structure = data.get("structure", [])

    sections: List[ReadmeSpecSection] = []
    toc = False
    for entry in structure:
        if entry.get("table-of-contents") or entry.get("table_of_contents"):
            toc = True
            continue
        sec_title = entry.get("section", "")
        description = entry.get("description")
        examples = entry.get("examples", [])
        sections.append(ReadmeSpecSection(title=sec_title, description=description, examples=examples))

    return ReadmeSpec(
        title=title,
        intro=intro,
        category=category,
        id_prefix=id_prefix,
        sections=sections,
        table_of_contents=toc,
    )


