"""Indexer: builds index.yml from annotations and filesystem."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .annotation_parser import discover_annotations, find_block_end_marker
from .fs_utils import compute_fingerprint, sha256_file
from .languages import get_language_for_file, get_supported_extensions
from .models import DirectoryIndex, Example, ExamplePart
from .readme_spec import ReadmeSpec
from .yaml_io import read_yaml, write_yaml


def find_source_files(root: Path) -> List[Path]:
    supported_exts = get_supported_extensions()
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in supported_exts]


def calculate_code_boundaries(annotation, file_lines: List[str]) -> tuple[int, int]:
    """Calculate (start,end) lines for the annotated code (1-based)."""
    code_start = annotation.end_line + 1

    if annotation.kind == 'function':
        lang_config = get_language_for_file(annotation.file_path)
        if lang_config:
            code_end = lang_config.function_parser.find_function_end(file_lines, code_start)
        else:
            code_end = code_start
    else:  # block
        block_end = find_block_end_marker(file_lines, code_start)
        if block_end:
            code_end = block_end - 1
            # Trim trailing empty lines within block
            while code_end >= code_start and not file_lines[code_end - 1].strip():
                code_end -= 1
            code_end = max(code_start, code_end)
        else:
            code_end = code_start

    return code_start, code_end


def build_examples_from_annotations(source_files: List[Path]) -> Dict[int, Example]:
    raw_annotations = discover_annotations(source_files)
    examples: Dict[int, Example] = {}

    grouped: Dict[int, List] = {}
    for ann in raw_annotations:
        ex_id = ann.metadata['id']
        grouped.setdefault(ex_id, []).append(ann)

    for ex_id, annotations in grouped.items():
        annotations.sort(key=lambda a: a.metadata.get('part', 1))

        kinds = {ann.kind for ann in annotations}
        if len(kinds) > 1:
            raise ValueError(f"Mixed annotation kinds for example {ex_id}")

        kind = annotations[0].kind
        if kind == 'function' and len(annotations) > 1:
            raise ValueError(f"Function example {ex_id} has multiple annotations")

        first_ann = annotations[0]
        title = first_ann.metadata.get('title')
        notes = first_ann.metadata.get('notes')
        request_details = first_ann.metadata.get('request-details')

        parts = []
        for ann in annotations:
            try:
                with open(ann.file_path, 'r', encoding='utf-8') as f:
                    file_lines = [line.rstrip('\n\r') for line in f.readlines()]
                start, end = calculate_code_boundaries(ann, file_lines)
                parts.append(
                    ExamplePart(
                        id=ex_id,
                        part=ann.metadata.get('part', 1),
                        file_path=ann.file_path,
                        code_start_line=start,
                        code_end_line=end,
                    )
                )
            except Exception as e:
                raise ValueError(f"Failed to process annotation in {ann.file_path}: {e}")

        if kind == 'block' and len(parts) > 1:
            expected = list(range(1, len(parts) + 1))
            actual = sorted(p.part for p in parts)
            if actual != expected:
                raise ValueError(f"Non-consecutive part numbers for block example {ex_id}")

        example = Example(
            id=ex_id,
            kind=kind,
            title=title,
            notes=notes,
            request_details=request_details,
            parts=parts,
        )
        examples[ex_id] = example

    return examples


def collect_attachments(root: Path) -> Dict[str, str]:
    attachments: Dict[str, str] = {}
    for dir_name in ("images", "http"):
        attach_dir = root / dir_name
        if attach_dir.exists() and attach_dir.is_dir():
            for file_path in attach_dir.rglob("*"):
                if file_path.is_file():
                    relative = file_path.relative_to(root).as_posix()
                    attachments[relative] = sha256_file(file_path)
    return attachments


def compute_example_hashes_and_fingerprints(examples: Dict[int, Example]) -> None:
    for example in examples.values():
        files = {part.file_path for part in example.parts}
        example.file_hashes = {path.as_posix(): sha256_file(path) for path in files}
        fingerprint_data = [
            str(example.id),
            example.kind,
            example.title or "",
            example.notes or "",
        ]
        fingerprint_data.extend(f"{p}:{h}" for p, h in sorted(example.file_hashes.items()))
        example.fingerprint = compute_fingerprint(fingerprint_data)


def build_directory_index(root: Path, spec: ReadmeSpec) -> DirectoryIndex:
    source_files = find_source_files(root)
    examples = build_examples_from_annotations(source_files)
    compute_example_hashes_and_fingerprints(examples)
    attachments = collect_attachments(root)

    index = DirectoryIndex(
        version="1",
        root=root,
        category=spec.category,
        id_prefix=spec.id_prefix,
        examples=examples,
        attachments=attachments,
    )

    sig_data: List[str] = []
    sig_data.extend(ex.fingerprint or "" for ex in sorted(examples.values(), key=lambda e: e.id))
    sig_data.extend(f"{p}:{h}" for p, h in sorted(attachments.items()))
    index.build_signature = compute_fingerprint(sig_data)
    return index


def read_existing_index(index_path: Path) -> Optional[DirectoryIndex]:
    if not index_path.exists():
        return None
    try:
        data = read_yaml(index_path)
        return DirectoryIndex.from_dict(data)
    except Exception:
        return None


def write_index(index_path: Path, index: DirectoryIndex) -> None:
    write_yaml(index_path, index.to_dict())

