"""Simplified annotation parser for @unsafe markers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any

import yaml

from .models import AnnotationKind


@dataclass
class RawAnnotation:
    """Raw annotation data before processing."""
    file_path: Path
    start_line: int  # 1-based line where @unsafe appears  
    end_line: int    # 1-based line where @/unsafe appears
    kind: AnnotationKind
    metadata: Dict[str, Any]


def find_annotation_boundaries(line: str) -> tuple[str, int] | None:
    """Find @unsafe marker in a line and return (kind, indentation).
    
    Returns None if no marker found, or (kind, indent_level) if found.
    """
    # Remove leading whitespace and count it
    stripped = line.lstrip()
    indent = len(line) - len(stripped)
    
    # Look for @unsafe[function] or @unsafe[block]
    match = re.search(r'@unsafe\[(function|block)\]', stripped)
    if match:
        return match.group(1), indent
    
    return None


def find_closing_marker(lines: List[str], start_idx: int, target_indent: int) -> int | None:
    """Find the matching @/unsafe marker at the same indentation level.
    
    Args:
        lines: File lines
        start_idx: Index where @unsafe was found (0-based)
        target_indent: Expected indentation level for closing marker
        
    Returns:
        Index of closing marker (0-based) or None if not found
    """
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        
        if indent == target_indent and '@/unsafe' in stripped:
            return i
    
    return None


def extract_yaml_content(lines: List[str], start_idx: int, end_idx: int) -> str:
    """Extract YAML content between @unsafe and @/unsafe markers.
    
    Args:
        lines: File lines
        start_idx: Index of @unsafe line (0-based)
        end_idx: Index of @/unsafe line (0-based)
        
    Returns:
        YAML content as string
    """
    yaml_lines = []
    
    for i in range(start_idx + 1, end_idx):
        line = lines[i]
        # Remove comment prefixes but preserve indentation structure
        cleaned = remove_comment_prefix(line)
        yaml_lines.append(cleaned)
    
    return '\n'.join(yaml_lines)


def remove_comment_prefix(line: str) -> str:
    """Remove comment prefix from a line while preserving indentation."""
    # Match common comment patterns and remove them
    patterns = [
        r'^(\s*)(#\s?)(.*)',      # Python comments: # content or #content
        r'^(\s*)(//\s?)(.*)',     # JS/TS comments: // content or //content  
        r'^(\s*)(/\*\s?)(.*)',    # Block comment start: /* content
        r'^(\s*)(\*\s?)(.*)',     # Block comment middle: * content
        r'^(\s*)(\*/\s?)(.*)',    # Block comment end: */ content
    ]
    
    for pattern in patterns:
        match = re.match(pattern, line)
        if match:
            # Keep original indentation + content after comment marker
            # The space is already included if present in the original
            return match.group(1) + match.group(3)
    
    return line


def parse_annotation_metadata(yaml_content: str) -> Dict[str, Any]:
    """Parse YAML metadata from annotation content."""
    if not yaml_content.strip():
        return {}
    
    try:
        # Try to parse the YAML
        data = yaml.safe_load(yaml_content) or {}
        
        # Validate and clean up the data
        result = {}
        
        # Required field
        if 'id' not in data:
            raise ValueError("Missing required 'id' field in annotation")
        
        result['id'] = int(data['id'])
        
        # Optional fields
        if 'title' in data:
            result['title'] = str(data['title'])
            
        if 'notes' in data:
            result['notes'] = str(data['notes']).rstrip()
            
        if 'request-details' in data:
            result['request-details'] = str(data['request-details'])
        elif 'request_details' in data:
            result['request-details'] = str(data['request_details'])
            
        if 'part' in data:
            result['part'] = int(data['part'])
            
        return result
        
    except yaml.YAMLError as e:
        # If YAML parsing fails, try to extract key fields manually
        # This handles cases where there are special characters in notes
        return _parse_yaml_fallback(yaml_content)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid annotation data: {e}")


def _parse_yaml_fallback(yaml_content: str) -> Dict[str, Any]:
    """Fallback parser for YAML with problematic content like markdown."""
    result = {}
    lines = yaml_content.split('\n')
    current_key = None
    current_value = []
    in_block_scalar = False
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped:
            if in_block_scalar:
                current_value.append('')
            continue
            
        # Check for key-value pairs
        if ':' in line and not in_block_scalar:
            if current_key and current_value:
                # Save previous key
                if current_key == 'notes':
                    result[current_key] = '\n'.join(current_value).rstrip()
                else:
                    result[current_key] = ' '.join(current_value).strip()
                current_value = []
            
            key, _, value = line.partition(':')
            current_key = key.strip()
            value = value.strip()
            
            if value == '|':
                # Block scalar
                in_block_scalar = True
            elif value:
                # Simple value
                if current_key in ('id', 'part'):
                    try:
                        result[current_key] = int(value)
                    except ValueError:
                        result[current_key] = value
                else:
                    result[current_key] = value
                current_key = None
                in_block_scalar = False
        else:
            # Continuation of current value
            if in_block_scalar:
                # For block scalars, preserve the line structure
                current_value.append(line.lstrip() if line.lstrip() else '')
            elif current_key:
                current_value.append(stripped)
    
    # Handle last key
    if current_key and current_value:
        if current_key == 'notes':
            result[current_key] = '\n'.join(current_value).rstrip()
        else:
            result[current_key] = ' '.join(current_value).strip()
    
    # Validate required fields
    if 'id' not in result:
        raise ValueError("Missing required 'id' field in annotation")
        
    # Ensure id is integer
    if not isinstance(result['id'], int):
        try:
            result['id'] = int(result['id'])
        except ValueError:
            raise ValueError(f"Invalid id value: {result['id']}")
    
    return result


def find_block_end_marker(lines: List[str], start_line: int) -> int | None:
    """Find @/unsafe[block] marker for block annotations.
    
    Args:
        lines: File lines
        start_line: Line where code block starts (1-based)
        
    Returns:
        Line number (1-based) of @/unsafe[block] marker, or None if not found
    """
    for i in range(start_line - 1, len(lines)):
        line = lines[i]
        if '@/unsafe[block]' in line:
            return i + 1  # Convert to 1-based
    
    return None


def parse_file_annotations(file_path: Path) -> List[RawAnnotation]:
    """Parse all @unsafe annotations from a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        raise ValueError(f"Cannot read file {file_path}: {e}")
    
    # Remove newlines for easier processing
    lines = [line.rstrip('\n\r') for line in lines]
    
    annotations = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        boundary = find_annotation_boundaries(line)
        
        if boundary:
            kind, indent = boundary
            
            # Find closing marker
            end_idx = find_closing_marker(lines, i, indent)
            if end_idx is None:
                raise ValueError(
                    f"Missing @/unsafe closing marker for annotation at {file_path}:{i+1}"
                )
            
            # Extract and parse YAML
            yaml_content = extract_yaml_content(lines, i, end_idx)
            metadata = parse_annotation_metadata(yaml_content)
            
            annotation = RawAnnotation(
                file_path=file_path,
                start_line=i + 1,       # Convert to 1-based
                end_line=end_idx + 1,   # Convert to 1-based  
                kind=kind,
                metadata=metadata
            )
            
            annotations.append(annotation)
            i = end_idx + 1
        else:
            i += 1
    
    return annotations


def discover_annotations(files: List[Path]) -> List[RawAnnotation]:
    """Discover all annotations across multiple files."""
    all_annotations = []
    
    for file_path in files:
        try:
            file_annotations = parse_file_annotations(file_path)
            all_annotations.extend(file_annotations)
        except Exception as e:
            # Log error but continue processing other files
            print(f"Warning: Failed to parse annotations in {file_path}: {e}")
    
    return all_annotations
