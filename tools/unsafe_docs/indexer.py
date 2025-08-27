"""Refactored indexer using the new modular components."""

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
    """Find all source files in supported languages."""
    supported_exts = get_supported_extensions()
    return [
        p for p in root.rglob("*") 
        if p.is_file() and p.suffix.lower() in supported_exts
    ]


def calculate_code_boundaries(annotation, file_lines: List[str]) -> tuple[int, int]:
    """Calculate code start and end lines for an annotation.
    
    Args:
        annotation: RawAnnotation object
        file_lines: Lines of the source file
        
    Returns:
        Tuple of (start_line, end_line) in 1-based indexing
    """
    # For both function and block, code starts after the @/unsafe marker
    code_start = annotation.end_line + 1
    
    if annotation.kind == 'function':
        # Use language-specific function parser
        lang_config = get_language_for_file(annotation.file_path)
        if lang_config:
            code_end = lang_config.function_parser.find_function_end(file_lines, code_start)
        else:
            # Fallback: assume single line
            code_end = code_start
    else:  # block
        # Find the @/unsafe[block] terminator
        block_end = find_block_end_marker(file_lines, code_start)
        if block_end:
            # Code ends before the terminator, skip empty lines
            code_end = block_end - 1
            while (code_end >= code_start and 
                   code_end <= len(file_lines) and 
                   not file_lines[code_end - 1].strip()):
                code_end -= 1
            code_end = max(code_start, code_end)
        else:
            # No terminator found, use start as end
            code_end = code_start
    
    return code_start, code_end


def build_examples_from_annotations(source_files: List[Path]) -> Dict[int, Example]:
    """Build Example objects from discovered annotations."""
    raw_annotations = discover_annotations(source_files)
    
    examples: Dict[int, Example] = {}
    
    # Group annotations by ID
    annotations_by_id: Dict[int, List] = {}
    for ann in raw_annotations:
        ex_id = ann.metadata['id']
        annotations_by_id.setdefault(ex_id, []).append(ann)
    
    # Process each example
    for ex_id, annotations in annotations_by_id.items():
        # Sort annotations by part number
        annotations.sort(key=lambda a: a.metadata.get('part', 1))
        
        # Validate consistency
        kinds = {ann.kind for ann in annotations}
        if len(kinds) > 1:
            raise ValueError(f"Mixed annotation kinds for example {ex_id}")
        
        kind = annotations[0].kind
        
        # For function kind, only one annotation is allowed
        if kind == 'function' and len(annotations) > 1:
            raise ValueError(f"Function example {ex_id} has multiple annotations")
        
        # Get metadata from first annotation (part 1)
        first_ann = annotations[0]
        title = first_ann.metadata.get('title')
        notes = first_ann.metadata.get('notes') 
        request_details = first_ann.metadata.get('request-details')
        
        # Build parts
        parts = []
        for ann in annotations:
            # Read file to calculate code boundaries
            try:
                with open(ann.file_path, 'r', encoding='utf-8') as f:
                    file_lines = f.readlines()
                file_lines = [line.rstrip('\n\r') for line in file_lines]
                
                code_start, code_end = calculate_code_boundaries(ann, file_lines)
                
                part = ExamplePart(
                    id=ex_id,
                    part=ann.metadata.get('part', 1),
                    file_path=ann.file_path,
                    code_start_line=code_start,
                    code_end_line=code_end
                )
                parts.append(part)
                
            except Exception as e:
                raise ValueError(f"Failed to process annotation in {ann.file_path}: {e}")
        
        # Validate part numbering for blocks
        if kind == 'block' and len(parts) > 1:
            expected_parts = list(range(1, len(parts) + 1))
            actual_parts = sorted(p.part for p in parts)
            if actual_parts != expected_parts:
                raise ValueError(f"Non-consecutive part numbers for block example {ex_id}")
        
        # Create example
        example = Example(
            id=ex_id,
            kind=kind,
            title=title,
            notes=notes,
            request_details=request_details,
            parts=parts
        )
        
        examples[ex_id] = example
    
    return examples


def collect_attachments(root: Path) -> Dict[str, str]:
    """Collect attachment files and their hashes."""
    attachments = {}
    
    for dir_name in ("images", "http"):
        attach_dir = root / dir_name
        if attach_dir.exists() and attach_dir.is_dir():
            for file_path in attach_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(root).as_posix()
                    attachments[relative_path] = sha256_file(file_path)
    
    return attachments


def compute_example_hashes_and_fingerprints(examples: Dict[int, Example]) -> None:
    """Compute file hashes and fingerprints for all examples."""
    for example in examples.values():
        # Collect unique files used by this example
        files = {part.file_path for part in example.parts}
        
        # Compute file hashes
        example.file_hashes = {}
        for file_path in files:
            example.file_hashes[file_path.as_posix()] = sha256_file(file_path)
        
        # Compute example fingerprint
        fingerprint_data = [
            str(example.id),
            example.kind,
            example.title or "",
            example.notes or "",
        ]
        fingerprint_data.extend(
            f"{path}:{hash_val}" 
            for path, hash_val in sorted(example.file_hashes.items())
        )
        
        example.fingerprint = compute_fingerprint(fingerprint_data)


def build_directory_index(root: Path, spec: ReadmeSpec) -> DirectoryIndex:
    """Build a complete directory index."""
    # Find source files
    source_files = find_source_files(root)
    
    # Build examples from annotations
    examples = build_examples_from_annotations(source_files)
    
    # Compute hashes and fingerprints
    compute_example_hashes_and_fingerprints(examples)
    
    # Collect attachments
    attachments = collect_attachments(root)
    
    # Create index
    index = DirectoryIndex(
        version="1",
        root=root,
        category=spec.category,
        id_prefix=spec.id_prefix,
        examples=examples,
        attachments=attachments
    )
    
    # Compute build signature
    signature_data = []
    signature_data.extend(
        ex.fingerprint or "" 
        for ex in sorted(examples.values(), key=lambda e: e.id)
    )
    signature_data.extend(
        f"{path}:{hash_val}" 
        for path, hash_val in sorted(attachments.items())
    )
    
    index.build_signature = compute_fingerprint(signature_data)
    
    return index


def read_existing_index(index_path: Path) -> Optional[DirectoryIndex]:
    """Read existing index file if it exists."""
    if not index_path.exists():
        return None
        
    try:
        data = read_yaml(index_path)
        return DirectoryIndex.from_dict(data)
    except Exception:
        return None


def write_index(index_path: Path, index: DirectoryIndex) -> None:
    """Write index to file."""
    write_yaml(index_path, index.to_dict())
