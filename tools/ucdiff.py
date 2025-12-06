#!/usr/bin/env python3
"""
ucdiff - Exercise diff tool for Unsafe Code Lab

Compare exercise versions to identify changes, drift, and missing specs.

PURPOSE:
    Visualize and analyze differences between exercise versions with
    project-aware intelligence. Helps with:
    - Identifying meaningful vs accidental changes
    - Propagating fixes across exercise versions
    - Finding missing e2e specs
    - Minimizing unnecessary drift between versions

USAGE:
    ucdiff <from> <to>              Compare two exercises
    ucdiff <from>..<to>             Same, using range syntax
    ucdiff v307                     Auto-compare with v306 (previous)
    ucdiff v306 v307                Compare consecutive versions
    ucdiff v206..v301               Cross-section comparison
    ucdiff r03                      Show all diffs within section
    ucdiff v301..v307 --file routes/restaurants.py
    ucdiff r03 --evolution restaurants.py

VERSION SYNTAX:
    v301        Exercise by absolute ID (section 3, exercise 1)
    r03/e01     Exercise by section/exercise
    r03         Entire section (iterates through all exercises)

PRIMARY FLAGS:
    (default)                  Tree view with +/- line stats
    -c, --code                 Show code changes (syntax-aware via difftastic)
    -o, --outline              Show function-level changes (added/modified/deleted)
    -r, --routes               Show only route-level changes (@bp.route decorators)
    -l, --list                 Just filenames (for scripting)
    --json                     Machine-readable JSON output

DISPLAY OPTIONS:
    -S, --side                 Side-by-side view for --code mode
    -F, --focused              Maximum noise reduction (--ignore-comments + context=1)
    --tool {difft,delta,icdiff} Diff tool for --code mode (default: difft)
    --ignore-comments          Ignore comment changes (difftastic only)
    -U, --context N            Context lines for diff (default: 3)
    -b, --boring               Show boring files at full brightness

FILTERS:
    --file, -f <pattern>       Only show files matching pattern
    --exclude <pattern>        Exclude files matching pattern
    --no-wiring                Skip config.py and routes/__init__.py
    --only-code                Only Python files, exclude fixtures/models
    --added-only               Only show added files
    --modified-only            Only show modified files
    --deleted-only             Only show deleted files

SPEC CHECKING:
    --check-specs              Warn when code changes but specs don't

EVOLUTION MODE:
    -e, --evolution [file]     Show file evolution matrix across versions
                               Without file: show all files in section
                               With pattern: filter to matching files
    -oe, -eo                   Evolution + function outline per transition
    -re, -er                   Evolution + route changes per transition

EXAMPLES:
    ucdiff v307                         # Auto-compare with v306 (tree view)
    ucdiff v307 -o                      # Function-level changes
    ucdiff v307 -r                      # Route-level changes only
    ucdiff v307 -c                      # Syntax-aware code diff
    ucdiff v307 -cS                     # Code diff, side-by-side
    ucdiff v307 -cF                     # Code diff, focused (max noise reduction)
    ucdiff v307 -l                      # Just list changed files
    ucdiff r03                          # Overview of all r03 changes
    ucdiff r03 -e                       # Evolution matrix for entire section
    ucdiff r03 -e routes/               # Evolution of routes/ directory
    ucdiff r03 -e orders.py             # Evolution of orders.py (partial match)
    ucdiff r03 -oe                      # Function evolution for section
    ucdiff r03 -re                      # Route evolution for section
    ucdiff r03 -re routes/              # Route evolution for routes/

EXIT CODES:
    0   Successful display
    2   Invalid arguments or version not found
"""

from __future__ import annotations

import argparse
import ast
import difflib
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

# =============================================================================
# Configuration
# =============================================================================

WEBAPP_BASE = Path("vulnerabilities/python/flask/confusion/webapp")
SPEC_BASE = Path("spec")

# Files to always filter (noise)
NOISE_FILES = {
    "__pycache__",
    ".DS_Store",
    ".pyc",
}

# Standard "wiring" files that often have trivial changes
WIRING_FILES = {
    "config.py",
    "routes/__init__.py",
    "__init__.py",
}

# Code-only filter (exclude fixtures, models, db setup)
NON_CODE_PATTERNS = {
    "fixtures.py",
    "models.py",
    "db.py",
    "storage.py",
}

# "Boring" files/directories to dim in tree view
BORING_FILES = {
    "__init__.py",
    "config.py",
}
BORING_DIRS = {
    "fixtures",
    "models",
    "database",
}

# Version patterns
VERSION_RE = re.compile(r"^v(\d{3})$")
SECTION_RE = re.compile(r"^r(\d{2})$")
EXERCISE_RE = re.compile(r"^r(\d{2})/e(\d{2})$")

# External tools
DIFFT_PATH = Path("/opt/homebrew/Cellar/difftastic/0.67.0/bin/difft")

console = Console()


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class VersionInfo:
    """Resolved version information."""
    id: str  # e.g., "v306"
    section: int  # e.g., 3
    exercise: int  # e.g., 6
    path: Path  # Full path to exercise directory
    spec_path: Path | None  # Path to spec directory, if exists
    exercise_name: str = ""  # e.g., "e06_domain_token_any_mailbox"


@dataclass
class LineStats:
    """Line change statistics for a file."""
    added: int = 0
    deleted: int = 0


@dataclass
class FunctionInfo:
    """Information about a function/method extracted from AST."""
    name: str
    lineno: int
    end_lineno: int
    decorators: list[str] = field(default_factory=list)
    route: str | None = None  # Extracted from @bp.route() or similar
    line_count: int = 0

    def __post_init__(self) -> None:
        self.line_count = self.end_lineno - self.lineno + 1


@dataclass
class FunctionChange:
    """Describes a change to a function between versions."""
    name: str
    change_type: str  # "added", "deleted", "modified"
    route: str | None = None
    old_lines: int = 0
    new_lines: int = 0


@dataclass
class DiffResult:
    """Complete diff result between two versions."""
    left: VersionInfo
    right: VersionInfo
    added: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    spec_drift: list[str] = field(default_factory=list)  # Code changed but no spec update
    line_stats: dict[str, LineStats] = field(default_factory=dict)  # Per-file line stats

    def is_empty(self) -> bool:
        return not (self.added or self.deleted or self.modified)

    def total_files(self) -> int:
        return len(self.added) + len(self.deleted) + len(self.modified)

    def total_lines_added(self) -> int:
        return sum(s.added for s in self.line_stats.values())

    def total_lines_deleted(self) -> int:
        return sum(s.deleted for s in self.line_stats.values())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "left": self.left.id,
            "right": self.right.id,
            "added": sorted(self.added),
            "deleted": sorted(self.deleted),
            "modified": sorted(self.modified),
            "spec_drift": sorted(self.spec_drift),
        }


# =============================================================================
# Version Resolution
# =============================================================================


def resolve_version(version_str: str) -> VersionInfo:
    """
    Resolve a version string to full version info.

    Supports formats:
    - v301 -> section 3, exercise 1
    - r03/e01 -> section 3, exercise 1
    """
    # Try vNNN format
    match = VERSION_RE.match(version_str)
    if match:
        num = int(match.group(1))
        section = num // 100
        exercise = num % 100

        section_dirs = list(WEBAPP_BASE.glob(f"r{section:02d}_*"))
        if not section_dirs:
            raise ValueError(f"Section r{section:02d} not found")

        section_dir = section_dirs[0]
        exercise_dirs = list(section_dir.glob(f"e{exercise:02d}_*"))
        if not exercise_dirs:
            raise ValueError(f"Exercise e{exercise:02d} not found in {section_dir.name}")

        exercise_path = exercise_dirs[0]
        spec_path = SPEC_BASE / f"v{num}"

        return VersionInfo(
            id=version_str,
            section=section,
            exercise=exercise,
            path=exercise_path,
            spec_path=spec_path if spec_path.exists() else None,
            exercise_name=exercise_path.name,
        )

    # Try r03/e01 format
    exercise_match = EXERCISE_RE.match(version_str)
    if exercise_match:
        section = int(exercise_match.group(1))
        exercise = int(exercise_match.group(2))
        version_id = f"v{section}{exercise:02d}"

        section_dirs = list(WEBAPP_BASE.glob(f"r{section:02d}_*"))
        if not section_dirs:
            raise ValueError(f"Section r{section:02d} not found")

        section_dir = section_dirs[0]
        exercise_dirs = list(section_dir.glob(f"e{exercise:02d}_*"))
        if not exercise_dirs:
            raise ValueError(f"Exercise e{exercise:02d} not found in {section_dir.name}")

        exercise_path = exercise_dirs[0]
        spec_path = SPEC_BASE / version_id

        return VersionInfo(
            id=version_id,
            section=section,
            exercise=exercise,
            path=exercise_path,
            spec_path=spec_path if spec_path.exists() else None,
            exercise_name=exercise_path.name,
        )

    raise ValueError(f"Invalid version format: {version_str}. Use v301 or r03/e01.")


def get_previous_version(version_str: str) -> str | None:
    """
    Get the previous version string for auto-prev convenience.

    For v307 returns v306. For v301 returns None (no previous in section).
    For cross-section (v301 -> v2XX), we don't auto-resolve.
    """
    match = VERSION_RE.match(version_str)
    if not match:
        return None

    num = int(match.group(1))
    section = num // 100
    exercise = num % 100

    if exercise <= 1:
        # v301 -> no previous in this section
        return None

    prev_num = num - 1
    prev_section = prev_num // 100

    # Only auto-prev within same section
    if prev_section != section:
        return None

    return f"v{prev_num}"


def list_section_versions(section_str: str) -> list[VersionInfo]:
    """List all versions in a section (e.g., r03 -> [v301, v302, ...])."""
    match = SECTION_RE.match(section_str)
    if not match:
        raise ValueError(f"Invalid section format: {section_str}. Use r03.")

    section = int(match.group(1))
    section_dirs = list(WEBAPP_BASE.glob(f"r{section:02d}_*"))
    if not section_dirs:
        raise ValueError(f"Section r{section:02d} not found")

    section_dir = section_dirs[0]
    versions = []

    for exercise_dir in sorted(section_dir.glob("e*_*")):
        match = re.match(r"e(\d{2})_", exercise_dir.name)
        if match:
            exercise = int(match.group(1))
            version_id = f"v{section}{exercise:02d}"
            spec_path = SPEC_BASE / version_id

            versions.append(VersionInfo(
                id=version_id,
                section=section,
                exercise=exercise,
                path=exercise_dir,
                spec_path=spec_path if spec_path.exists() else None,
                exercise_name=exercise_dir.name,
            ))

    return versions


def get_version_range(from_ver: str, to_ver: str) -> list[VersionInfo]:
    """Get all versions in a range, inclusive."""
    left = resolve_version(from_ver)
    right = resolve_version(to_ver)

    versions = []
    from_num = int(left.id[1:])
    to_num = int(right.id[1:])

    import contextlib
    for num in range(from_num, to_num + 1):
        with contextlib.suppress(ValueError):
            versions.append(resolve_version(f"v{num}"))

    return versions


# =============================================================================
# Directory Comparison
# =============================================================================


def compare_directories(
    left: VersionInfo,
    right: VersionInfo,
    file_filter: str | None = None,
    exclude_pattern: str | None = None,
    no_wiring: bool = False,
    only_code: bool = False,
) -> DiffResult:
    """Compare two version directories recursively."""
    result = DiffResult(left=left, right=right)

    def should_include(filepath: str) -> bool:
        """Check if file should be included based on filters."""
        name = Path(filepath).name

        # Always exclude noise
        if name in NOISE_FILES or name.endswith(".pyc"):
            return False

        # File filter (positive match)
        if file_filter and file_filter not in filepath:
            return False

        # Exclude pattern
        if exclude_pattern and exclude_pattern in filepath:
            return False

        # No wiring filter
        if no_wiring and filepath in WIRING_FILES:
            return False

        # Only code filter
        return not (only_code and name in NON_CODE_PATTERNS)

    def walk_dircmp(dcmp: filecmp.dircmp, prefix: str = ""):
        left_path = Path(dcmp.left)
        right_path = Path(dcmp.right)

        # Files only on left (deleted in right)
        for name in dcmp.left_only:
            path = prefix + name
            if (left_path / name).is_dir():
                for f in (left_path / name).rglob("*"):
                    if f.is_file():
                        rel = path + "/" + str(f.relative_to(left_path / name))
                        if should_include(rel):
                            result.deleted.append(rel)
            elif should_include(path):
                result.deleted.append(path)

        # Files only on right (added in right)
        for name in dcmp.right_only:
            path = prefix + name
            if (right_path / name).is_dir():
                for f in (right_path / name).rglob("*"):
                    if f.is_file():
                        rel = path + "/" + str(f.relative_to(right_path / name))
                        if should_include(rel):
                            result.added.append(rel)
            elif should_include(path):
                result.added.append(path)

        # Files that differ
        for name in dcmp.diff_files:
            path = prefix + name
            if should_include(path):
                result.modified.append(path)

        # Recurse into subdirectories
        for subdir, sub_dcmp in dcmp.subdirs.items():
            walk_dircmp(sub_dcmp, prefix + subdir + "/")

    dcmp = filecmp.dircmp(left.path, right.path)
    walk_dircmp(dcmp)

    return result


def compare_specs(left: VersionInfo, right: VersionInfo) -> set[str]:
    """
    Compare spec directories between two versions.

    Returns set of .http files that changed in specs.
    """
    changed_specs: set[str] = set()

    if not left.spec_path or not right.spec_path:
        return changed_specs

    if not left.spec_path.exists() or not right.spec_path.exists():
        return changed_specs

    dcmp = filecmp.dircmp(left.spec_path, right.spec_path)

    def walk_specs(d: filecmp.dircmp, prefix: str = "") -> None:
        for name in d.diff_files:
            if name.endswith(".http"):
                changed_specs.add(prefix + name)
        for name in d.left_only + d.right_only:
            path = Path(d.left) / name
            if path.is_file() and name.endswith(".http"):
                changed_specs.add(prefix + name)
        for subdir, sub_dcmp in d.subdirs.items():
            walk_specs(sub_dcmp, prefix + subdir + "/")

    walk_specs(dcmp)
    return changed_specs


def detect_spec_drift(result: DiffResult) -> list[str]:
    """
    Detect code files that changed but have no corresponding spec change.

    Returns list of code files that may need spec updates.
    """
    # Get changed spec files
    spec_changes = compare_specs(result.left, result.right)

    # Code files that changed (excluding non-code like __init__.py, config.py)
    code_patterns = {".py"}
    ignore_patterns = {"__init__.py", "config.py", "fixtures.py", "models.py"}

    code_changed: list[str] = []
    for f in result.added + result.modified:
        if any(f.endswith(ext) for ext in code_patterns):
            name = Path(f).name
            if name not in ignore_patterns:
                code_changed.append(f)

    # If code changed but no specs changed, flag as potential drift
    if code_changed and not spec_changes:
        return code_changed

    return []


def calculate_line_stats(left_path: Path, right_path: Path, filepath: str) -> LineStats:
    """Calculate line change statistics for a file using difflib."""
    left_file = left_path / filepath
    right_file = right_path / filepath

    try:
        if not left_file.exists():
            # Added file - count all lines as added
            with open(right_file, encoding="utf-8", errors="replace") as f:
                lines = len(f.readlines())
            return LineStats(added=lines, deleted=0)

        if not right_file.exists():
            # Deleted file - count all lines as deleted
            with open(left_file, encoding="utf-8", errors="replace") as f:
                lines = len(f.readlines())
            return LineStats(added=0, deleted=lines)

        # Modified file - use difflib to count +/-
        with open(left_file, encoding="utf-8", errors="replace") as f:
            left_lines = f.readlines()
        with open(right_file, encoding="utf-8", errors="replace") as f:
            right_lines = f.readlines()

        diff = list(difflib.unified_diff(left_lines, right_lines, lineterm=""))
        added = 0
        deleted = 0
        for line in diff:
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                deleted += 1

        return LineStats(added=added, deleted=deleted)
    except Exception:
        return LineStats()


def calculate_all_line_stats(result: DiffResult) -> None:
    """Calculate line stats for all files in the diff result."""
    left_path = result.left.path
    right_path = result.right.path

    for filepath in result.added:
        result.line_stats[filepath] = calculate_line_stats(left_path, right_path, filepath)

    for filepath in result.deleted:
        result.line_stats[filepath] = calculate_line_stats(left_path, right_path, filepath)

    for filepath in result.modified:
        result.line_stats[filepath] = calculate_line_stats(left_path, right_path, filepath)


def is_boring_file(filepath: str) -> bool:
    """Check if a file is considered 'boring' (should be dimmed)."""
    name = Path(filepath).name
    if name in BORING_FILES:
        return True

    # Check if any parent directory is in BORING_DIRS
    parts = Path(filepath).parts
    return any(part in BORING_DIRS for part in parts)


# =============================================================================
# Function/Route Extraction (AST-based)
# =============================================================================


def extract_route_from_decorator(decorator: ast.expr) -> str | None:
    """
    Extract route path from a decorator like @bp.route('/path') or @app.get('/path').

    Supports patterns:
    - @bp.route('/path')
    - @bp.route('/path', methods=['GET'])
    - @app.get('/path')
    - @router.post('/path')
    """
    if not isinstance(decorator, ast.Call):
        return None

    func = decorator.func

    # Handle bp.route(), app.get(), router.post() etc.
    if isinstance(func, ast.Attribute):
        method_name = func.attr
        # Common route methods
        route_methods = {"route", "get", "post", "put", "delete", "patch"}
        if method_name in route_methods and decorator.args:
            first_arg = decorator.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                return first_arg.value

    return None


def extract_decorator_name(decorator: ast.expr) -> str:
    """Extract a readable decorator name from AST node."""
    if isinstance(decorator, ast.Name):
        return f"@{decorator.id}"
    elif isinstance(decorator, ast.Attribute):
        # e.g., @bp.route -> bp.route
        parts: list[str] = []
        node: ast.expr = decorator
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return "@" + ".".join(reversed(parts))
    elif isinstance(decorator, ast.Call):
        # Recurse into the call's function
        return extract_decorator_name(decorator.func)
    return "@unknown"


def extract_functions_from_code(code: str) -> dict[str, FunctionInfo]:
    """
    Extract function definitions from Python source code using AST.

    Returns dict mapping function name to FunctionInfo.
    For methods, includes class prefix: "ClassName.method_name"
    """
    functions: dict[str, FunctionInfo] = {}

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return functions

    def process_function(node: ast.FunctionDef | ast.AsyncFunctionDef, prefix: str = "") -> None:
        """Process a function/method node."""
        full_name = f"{prefix}{node.name}" if prefix else node.name

        # Extract decorators
        decorators: list[str] = []
        route: str | None = None

        for dec in node.decorator_list:
            dec_name = extract_decorator_name(dec)
            decorators.append(dec_name)

            # Try to extract route path
            if route is None:
                route = extract_route_from_decorator(dec)

        # Get end line (ast.FunctionDef has end_lineno in Python 3.8+)
        end_line = getattr(node, "end_lineno", node.lineno)

        functions[full_name] = FunctionInfo(
            name=full_name,
            lineno=node.lineno,
            end_lineno=end_line,
            decorators=decorators,
            route=route,
        )

    def visit_node(node: ast.AST, class_prefix: str = "") -> None:
        """Recursively visit AST nodes."""
        if isinstance(node, ast.ClassDef):
            # Process methods within the class
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                    process_function(child, prefix=f"{node.name}.")
                elif isinstance(child, ast.ClassDef):
                    # Nested class
                    visit_node(child, class_prefix=f"{node.name}.")
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            process_function(node, prefix=class_prefix)

    # Visit top-level nodes
    for node in ast.iter_child_nodes(tree):
        visit_node(node)

    return functions


def extract_functions_from_file(filepath: Path) -> dict[str, FunctionInfo]:
    """Extract functions from a Python file."""
    if not filepath.exists() or filepath.suffix != ".py":
        return {}

    try:
        code = filepath.read_text(encoding="utf-8", errors="replace")
        return extract_functions_from_code(code)
    except Exception:
        return {}


def calculate_function_changes(
    left_path: Path,
    right_path: Path,
    filepath: str,
) -> list[FunctionChange]:
    """
    Calculate function-level changes between two versions of a file.

    Returns list of FunctionChange objects describing what changed.
    """
    left_file = left_path / filepath
    right_file = right_path / filepath

    left_funcs = extract_functions_from_file(left_file)
    right_funcs = extract_functions_from_file(right_file)

    changes: list[FunctionChange] = []

    # Added functions
    for name, info in right_funcs.items():
        if name not in left_funcs:
            changes.append(FunctionChange(
                name=name,
                change_type="added",
                route=info.route,
                new_lines=info.line_count,
            ))

    # Deleted functions
    for name, info in left_funcs.items():
        if name not in right_funcs:
            changes.append(FunctionChange(
                name=name,
                change_type="deleted",
                route=info.route,
                old_lines=info.line_count,
            ))

    # Modified functions (exist in both, compare content)
    for name in left_funcs.keys() & right_funcs.keys():
        left_info = left_funcs[name]
        right_info = right_funcs[name]

        # Check if the function body changed by comparing line counts and content
        # We use a simple heuristic: if line count changed significantly, it's modified
        # For more accuracy, we'd need to extract and compare the actual source
        if left_info.line_count != right_info.line_count:
            changes.append(FunctionChange(
                name=name,
                change_type="modified",
                route=right_info.route or left_info.route,
                old_lines=left_info.line_count,
                new_lines=right_info.line_count,
            ))
        else:
            # Line counts match but content might still differ
            # Extract actual source and compare
            try:
                left_code = left_file.read_text(encoding="utf-8", errors="replace")
                right_code = right_file.read_text(encoding="utf-8", errors="replace")

                left_lines = left_code.splitlines()
                right_lines = right_code.splitlines()

                # Get the function body lines
                left_body = left_lines[left_info.lineno - 1:left_info.end_lineno]
                right_body = right_lines[right_info.lineno - 1:right_info.end_lineno]

                if left_body != right_body:
                    changes.append(FunctionChange(
                        name=name,
                        change_type="modified",
                        route=right_info.route or left_info.route,
                        old_lines=left_info.line_count,
                        new_lines=right_info.line_count,
                    ))
            except Exception:
                pass  # If we can't compare, skip

    return changes


# =============================================================================
# Output Modes
# =============================================================================


def show_tree(
    result: DiffResult,
    check_specs: bool = False,
    show_hints: bool = True,
    highlight_boring: bool = False,
) -> None:
    """
    Show tree view of changes with status indicators and line stats.

    Args:
        result: The diff result to display
        check_specs: Whether to show spec drift warnings
        show_hints: Whether to show integration hints
        highlight_boring: If True, show boring files at full brightness
    """
    console.print()

    # Calculate line stats if not already done
    if not result.line_stats:
        calculate_all_line_stats(result)

    # Build file tree structure
    # Keys are directory paths (or "" for root), values are lists of (filename, status, filepath)
    tree_structure: dict[str, list[tuple[str, str, str]]] = {}

    def add_to_tree(filepath: str, status: str) -> None:
        """Add a file to the tree structure."""
        path = Path(filepath)
        parent = str(path.parent) if path.parent != Path(".") else ""
        tree_structure.setdefault(parent, []).append((path.name, status, filepath))

    # Add all files to tree structure
    for f in result.added:
        add_to_tree(f, "A")
    for f in result.deleted:
        add_to_tree(f, "D")
    for f in result.modified:
        add_to_tree(f, "M")

    if not tree_structure:
        console.print(f"[bold cyan]{result.left.id}[/] -> [bold cyan]{result.right.id}[/]")
        console.print("[dim]No differences[/]")
        return

    # Styles
    status_styles = {
        "A": Style(color="green"),
        "M": Style(color="yellow"),
        "D": Style(color="red"),
    }
    dim_style = Style(dim=True)
    connector_style = Style(dim=True)

    # Create root tree
    header = f"[bold cyan]{result.left.id}[/] -> [bold cyan]{result.right.id}[/]"
    tree = Tree(header, guide_style=connector_style)

    # Sort directories for consistent output
    sorted_dirs = sorted(tree_structure.keys())

    # Track directory nodes for nested structure
    dir_nodes: dict[str, Tree] = {"": tree}

    def get_or_create_dir_node(dir_path: str) -> Tree:
        """Get or create a tree node for a directory path."""
        if dir_path in dir_nodes:
            return dir_nodes[dir_path]

        # Create parent first if needed
        parent_path = str(Path(dir_path).parent) if Path(dir_path).parent != Path(".") else ""
        parent_node = get_or_create_dir_node(parent_path)

        # Create this directory node
        dir_name = Path(dir_path).name
        is_boring = dir_name in BORING_DIRS

        if is_boring and not highlight_boring:
            label = Text(f"{dir_name}/", style=dim_style)
        else:
            label = Text(f"{dir_name}/", style="bold")

        node = parent_node.add(label)
        dir_nodes[dir_path] = node
        return node

    # Find the maximum filename length for alignment
    max_name_len = 0
    for files in tree_structure.values():
        for filename, _, _ in files:
            max_name_len = max(max_name_len, len(filename))
    # Add some padding
    max_name_len = min(max_name_len + 2, 35)  # Cap at 35 chars

    # Add files to tree
    for dir_path in sorted_dirs:
        parent_node = get_or_create_dir_node(dir_path) if dir_path else tree

        # Sort files in this directory
        files = sorted(tree_structure[dir_path], key=lambda x: x[0])

        for filename, status, filepath in files:
            stats = result.line_stats.get(filepath, LineStats())
            is_boring = is_boring_file(filepath)

            # Build the file entry text
            file_text = Text()

            # Filename with padding
            name_padded = filename.ljust(max_name_len)

            # Apply styling based on boring status
            if is_boring and not highlight_boring:
                file_text.append(name_padded, style=dim_style)
                file_text.append(f" {status}  ", style=dim_style)
                stats_str = f"+{stats.added}/-{stats.deleted}"
                file_text.append(stats_str, style=dim_style)
            else:
                file_text.append(name_padded)
                file_text.append(f" {status}  ", style=status_styles.get(status, ""))
                # Stats with color
                file_text.append(f"+{stats.added}", style="green")
                file_text.append("/", style="dim")
                file_text.append(f"-{stats.deleted}", style="red")

            parent_node.add(file_text)

    console.print(tree)

    # Summary footer
    total_added = result.total_lines_added()
    total_deleted = result.total_lines_deleted()
    console.print()
    console.print(
        f"[dim]Summary:[/] {result.total_files()} files changed, "
        f"[green]+{total_added}[/]/[red]-{total_deleted}[/]"
    )

    # Spec drift warning
    if check_specs and result.spec_drift:
        console.print()
        count = len(result.spec_drift)
        console.print(
            f"[yellow]Warning: Potential spec gap: "
            f"{count} code file{'s' if count != 1 else ''} changed with no spec updates[/]"
        )

    # Integration hints
    if show_hints and not result.is_empty():
        _show_integration_hints(result)


def show_summary(result: DiffResult, check_specs: bool = False, show_hints: bool = True):
    """Show quick summary of changes (compact table format)."""
    console.print()

    # Create a nice header panel
    header = f"[bold cyan]{result.left.id}[/] → [bold cyan]{result.right.id}[/]"
    subtitle = f"{result.left.exercise_name} → {result.right.exercise_name}"

    console.print(Panel(header, subtitle=subtitle, style="dim"))

    if result.is_empty():
        console.print("  [dim]No differences[/]")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Type", style="bold", width=12)
    table.add_column("Count", justify="right", width=4)
    table.add_column("Files")

    if result.added:
        files_preview = ", ".join(result.added[:3])
        if len(result.added) > 3:
            files_preview += f" (+{len(result.added) - 3} more)"
        table.add_row("[green]Added[/]", str(len(result.added)), files_preview)

    if result.deleted:
        files_preview = ", ".join(result.deleted[:3])
        if len(result.deleted) > 3:
            files_preview += f" (+{len(result.deleted) - 3} more)"
        table.add_row("[red]Deleted[/]", str(len(result.deleted)), files_preview)

    if result.modified:
        files_preview = ", ".join(result.modified[:3])
        if len(result.modified) > 3:
            files_preview += f" (+{len(result.modified) - 3} more)"
        table.add_row("[yellow]Modified[/]", str(len(result.modified)), files_preview)

    console.print(table)
    console.print(f"\n[dim]Total: {result.total_files()} files changed[/]")

    # Spec drift warning
    if check_specs and result.spec_drift:
        console.print()
        count = len(result.spec_drift)
        console.print(
            f"[yellow]Warning: Potential spec gap: "
            f"{count} code file{'s' if count != 1 else ''} changed with no spec updates[/]"
        )

    # Integration hints
    if show_hints and not result.is_empty():
        _show_integration_hints(result)


def _show_integration_hints(result: DiffResult) -> None:
    """Show helpful commands based on what changed."""
    console.print()

    hints: list[str] = []
    right_id = result.right.id

    # Check for route changes
    route_files = [f for f in result.modified + result.added if "routes" in f]
    if route_files:
        hints.append(f"Run: uctest {right_id}/")

    # Check for spec drift
    if result.spec_drift:
        hints.append(f"Run: ucsync {right_id}")

    # Check for demo-related files (http/ directory changes)
    demo_files = [f for f in result.modified + result.added if "/http/" in f]
    if demo_files:
        # Extract section from right version
        section = result.right.section
        exercise = result.right.exercise
        hints.append(f"Run: ucdemo r{section:02d}/e{exercise:02d}")

    if hints:
        for hint in hints[:3]:  # Limit to 3 hints
            console.print(f"[dim]Hint: {hint}[/]")


def show_json(result: DiffResult) -> None:
    """Output machine-readable JSON."""
    print(json.dumps(result.to_dict(), indent=2))


def show_stat(result: DiffResult):
    """Show git-style stat view."""
    console.print()
    console.print(f"[bold]{result.left.id} → {result.right.id}[/]")
    console.print()

    try:
        proc = subprocess.run(
            ["git", "diff", "--no-index", "--stat", "--stat-width=100",
             str(result.left.path), str(result.right.path)],
            capture_output=True,
            text=True,
        )
        output = proc.stdout
        # Clean up paths for readability
        output = output.replace(str(result.left.path) + "/", "")
        output = output.replace(str(result.right.path) + "/", "")
        console.print(output)
    except Exception as e:
        console.print(f"[red]Error running git diff: {e}[/]")


def show_files(result: DiffResult):
    """Just list changed files (good for scripting)."""
    for f in sorted(result.added):
        console.print(f"[green]A[/] {f}")
    for f in sorted(result.deleted):
        console.print(f"[red]D[/] {f}")
    for f in sorted(result.modified):
        console.print(f"[yellow]M[/] {f}")


def show_unified(
    result: DiffResult,
    file_filter: str | None = None,
    context_lines: int = 3,
) -> None:
    """Show unified diff for modified files."""
    files_to_show = result.modified
    if file_filter:
        files_to_show = [f for f in files_to_show if file_filter in f]

    for filepath in sorted(files_to_show):
        left_file = result.left.path / filepath
        right_file = result.right.path / filepath

        console.print(f"\n[bold blue]{'─' * 60}[/]")
        console.print(f"[bold]{filepath}[/]")
        console.print(f"[bold blue]{'─' * 60}[/]")

        try:
            cmd = [
                "git", "diff", "--no-index", "--color=always",
                f"-U{context_lines}",
                str(left_file), str(right_file),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            # Skip the header lines (first 4)
            lines = proc.stdout.split("\n")
            if len(lines) > 4:
                # Use print() directly to preserve ANSI codes (console.print escapes them)
                print("\n".join(lines[4:]))
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


def show_side_by_side(
    result: DiffResult,
    file_filter: str | None = None,
    context_lines: int = 3,
) -> None:
    """
    Show side-by-side diff using icdiff, falls back to unified.

    Args:
        result: The diff result to display
        file_filter: Optional pattern to filter files
        context_lines: Number of context lines
    """
    if not shutil.which("icdiff"):
        console.print("[dim]Using unified diff (install icdiff for side-by-side output)[/]")
        show_unified(result, file_filter, context_lines)
        return

    files_to_show = result.modified
    if file_filter:
        files_to_show = [f for f in files_to_show if file_filter in f]

    for filepath in sorted(files_to_show):
        left_file = result.left.path / filepath
        right_file = result.right.path / filepath

        console.print(f"\n[bold blue]{'─' * 60}[/]")
        console.print(f"[bold]{filepath}[/]")
        console.print(f"[bold blue]{'─' * 60}[/]")

        try:
            cmd = [
                "icdiff",
                "--line-numbers",
                "--cols=160",
                f"-U{context_lines}",
                str(left_file),
                str(right_file),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            # Use print() directly to preserve ANSI codes (console.print escapes them)
            print(proc.stdout, end='')
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


def show_syntax_diff(
    result: DiffResult,
    file_filter: str | None = None,
    context_lines: int = 3,
    display: str = "inline",
    ignore_comments: bool = False,
) -> None:
    """
    Show syntax-aware diff using difftastic, falls back to unified.

    Args:
        result: The diff result to display
        file_filter: Optional pattern to filter files
        context_lines: Number of context lines
        display: Display mode - "inline" or "side-by-side"
        ignore_comments: Skip comment-only changes (difftastic --ignore-comments)
    """
    difft_cmd: str | None = None

    if DIFFT_PATH.exists():
        difft_cmd = str(DIFFT_PATH)
    else:
        difft = shutil.which("difft")
        if difft:
            difft_cmd = difft

    if not difft_cmd:
        console.print("[dim]Using unified diff (install difftastic for syntax-aware output)[/]")
        show_unified(result, file_filter, context_lines)
        return

    files_to_show = result.modified
    if file_filter:
        files_to_show = [f for f in files_to_show if file_filter in f]

    for filepath in sorted(files_to_show):
        left_file = result.left.path / filepath
        right_file = result.right.path / filepath

        console.print(f"\n[bold blue]{'─' * 60}[/]")
        console.print(f"[bold]{filepath}[/]")
        console.print(f"[bold blue]{'─' * 60}[/]")

        try:
            cmd = [
                difft_cmd,
                "--color", "always",
                "--display", display,
                "--context", str(context_lines),
            ]
            if ignore_comments:
                cmd.append("--ignore-comments")
            cmd.extend([str(left_file), str(right_file)])
            proc = subprocess.run(cmd, capture_output=True, text=True)
            # Use print() directly to preserve ANSI codes (console.print escapes them)
            print(proc.stdout, end='')
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


def show_delta(
    result: DiffResult,
    file_filter: str | None = None,
    context_lines: int = 3,
    side_by_side: bool = False,
) -> None:
    """
    Show diff via delta, falls back to unified.

    Args:
        result: The diff result to display
        file_filter: Optional pattern to filter files
        context_lines: Number of context lines
        side_by_side: Use side-by-side display with word-level highlighting
    """
    if not shutil.which("delta"):
        console.print("[dim]Using unified diff (install git-delta for rich output)[/]")
        show_unified(result, file_filter, context_lines)
        return

    files_to_show = result.modified
    if file_filter:
        files_to_show = [f for f in files_to_show if file_filter in f]

    for filepath in sorted(files_to_show):
        left_file = result.left.path / filepath
        right_file = result.right.path / filepath

        console.print(f"\n[bold blue]{'─' * 60}[/]")
        console.print(f"[bold]{filepath}[/]")
        console.print(f"[bold blue]{'─' * 60}[/]")

        try:
            # Use git diff and pipe through delta
            proc = subprocess.run(
                [
                    "git", "diff", "--no-index",
                    f"-U{context_lines}",
                    str(left_file), str(right_file),
                ],
                capture_output=True,
                text=True,
            )
            # Get terminal width for delta
            try:
                term_width = os.get_terminal_size().columns
            except OSError:
                term_width = 160
            delta_cmd = ["delta", "--no-gitconfig", f"--width={term_width}"]
            if side_by_side:
                delta_cmd.append("--side-by-side")
            proc2 = subprocess.run(
                delta_cmd,
                input=proc.stdout,
                capture_output=True,
                text=True,
            )
            # Use print() directly to preserve ANSI codes (console.print escapes them)
            print(proc2.stdout, end='')
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


def resolve_file_pattern(version_path: Path, pattern: str) -> list[Path]:
    """
    Resolve a file pattern to actual files in a version directory.

    Supports:
    - Exact paths: routes/orders.py
    - Partial names: orders.py (searches recursively)
    - Directory patterns: routes/ (all files in directory)
    - Glob patterns: routes/*.py
    """
    # Try exact path first
    exact_path = version_path / pattern
    if exact_path.exists():
        if exact_path.is_file():
            return [exact_path]
        elif exact_path.is_dir():
            # Return all Python files in directory
            return sorted(exact_path.rglob("*.py"))

    # Try glob pattern
    if "*" in pattern or "?" in pattern:
        matches = sorted(version_path.glob(pattern))
        if matches:
            return [m for m in matches if m.is_file()]

    # Try partial name match (search recursively)
    # e.g., "orders.py" finds "routes/orders.py"
    matches = []
    for f in version_path.rglob("*"):
        if f.is_file() and pattern in f.name:
            matches.append(f)

    return sorted(matches)


def get_file_diff_stats(left_file: Path, right_file: Path) -> tuple[int, int] | None:
    """
    Get insertion/deletion counts for a file pair.
    Returns (insertions, deletions) or None if no changes.
    """
    try:
        proc = subprocess.run(
            ["git", "diff", "--no-index", "--numstat", str(left_file), str(right_file)],
            capture_output=True,
            text=True,
        )
        if proc.stdout.strip():
            parts = proc.stdout.strip().split("\t")
            if len(parts) >= 2:
                ins = int(parts[0]) if parts[0] != "-" else 0
                dels = int(parts[1]) if parts[1] != "-" else 0
                if ins > 0 or dels > 0:
                    return (ins, dels)
        return None
    except Exception:
        return None


def show_evolution(
    versions: list[VersionInfo],
    file_pattern: str | None = None,
    outline_mode: bool = False,
    routes_only: bool = False,
):
    """
    Show how files evolved across multiple versions in a compact matrix format.

    Supports partial file names, directory patterns, and globs.
    When file_pattern is None, shows evolution of all changed files.

    Args:
        versions: List of versions to compare
        file_pattern: Optional file filter (partial name, directory, glob)
        outline_mode: If True, show function-level changes instead of line stats
        routes_only: If True (with outline_mode), only show route handlers
    """
    # Collect all files across all versions
    all_rel_paths: set[str] = set()

    if file_pattern:
        # Filter to matching files
        for v in versions:
            resolved = resolve_file_pattern(v.path, file_pattern)
            for f in resolved:
                rel = str(f.relative_to(v.path))
                all_rel_paths.add(rel)
        title = f"Evolution of [cyan]{file_pattern}[/cyan]"
    else:
        # Collect ALL Python files that exist in any version
        for v in versions:
            for f in v.path.rglob("*.py"):
                rel = str(f.relative_to(v.path))
                # Skip __pycache__ and other noise
                if "__pycache__" not in rel:
                    all_rel_paths.add(rel)
        title = "Section Evolution"

    if not all_rel_paths:
        console.print(f"[yellow]No files found[/]")
        return

    # Build evolution matrix: version_transition -> file -> change_info
    # Change info: None (no change), "+" (added), "-" (deleted), (ins, dels) tuple
    transitions = []
    for i in range(len(versions) - 1):
        transitions.append((versions[i], versions[i + 1]))

    # Build matrix data structure
    matrix: dict[str, list[tuple[str, any]]] = {}  # file -> [(transition_label, change_info), ...]

    for rel_path in sorted(all_rel_paths):
        file_changes = []
        for left, right in transitions:
            left_file = left.path / rel_path
            right_file = right.path / rel_path
            trans_label = f"{left.id}→{right.id}"

            if not left_file.exists() and not right_file.exists():
                file_changes.append((trans_label, None))
            elif not left_file.exists():
                file_changes.append((trans_label, "+"))  # Added
            elif not right_file.exists():
                file_changes.append((trans_label, "-"))  # Deleted
            else:
                stats = get_file_diff_stats(left_file, right_file)
                file_changes.append((trans_label, stats))

        # Only include files that have at least one change
        if any(change is not None for _, change in file_changes):
            matrix[rel_path] = file_changes

    if not matrix:
        console.print(f"[dim]No changes found[/]")
        return

    # Display header
    console.print(Panel(f"[bold]{title}[/]"))
    console.print()

    if outline_mode:
        # Function-level evolution: show changes grouped by version transition
        _show_evolution_outline(versions, matrix, routes_only)
    else:
        # Compact matrix view
        _show_evolution_matrix(transitions, matrix)


def _build_tree_structure(paths: list[str]) -> list[tuple[str, str, bool]]:
    """
    Build tree structure from file paths.

    Returns list of (display_name, full_path, is_last_in_group) tuples.
    Groups files by directory with tree-like indentation.

    Smart handling:
    - If all files share the same single top-level directory, strip it
    - Only show directory headers when there are multiple directories
    """
    from collections import defaultdict

    sorted_paths = sorted(paths)

    # Check if all files share the same single top-level directory
    # If so, strip it to avoid redundant nesting
    if all("/" in p for p in sorted_paths):
        top_dirs = set(p.split("/")[0] for p in sorted_paths)
        if len(top_dirs) == 1:
            # All in same directory - strip the common prefix
            common_dir = list(top_dirs)[0]
            sorted_paths = ["/".join(p.split("/")[1:]) for p in sorted_paths]
            # Rebuild the mapping
            path_map = {new: old for new, old in zip(sorted_paths, sorted(paths))}
        else:
            path_map = {p: p for p in sorted_paths}
    else:
        path_map = {p: p for p in sorted_paths}

    # Group files by their parent directory
    by_dir: dict[str, list[tuple[str, str]]] = defaultdict(list)
    root_files: list[tuple[str, str]] = []  # (display, full_path)

    for display_path in sorted_paths:
        full_path = path_map[display_path]
        if "/" in display_path:
            parts = display_path.split("/")
            dir_name = parts[0]
            rest = "/".join(parts[1:])
            by_dir[dir_name].append((rest, full_path))
        else:
            root_files.append((display_path, full_path))

    result = []

    # Add root-level files first
    for i, (display, full_path) in enumerate(root_files):
        is_last = (i == len(root_files) - 1) and not by_dir
        result.append((display, full_path, is_last))

    # Add directories with their children
    dir_names = sorted(by_dir.keys())
    for dir_idx, dir_name in enumerate(dir_names):
        is_last_dir = dir_idx == len(dir_names) - 1
        files = by_dir[dir_name]

        # Directory header
        result.append((f"[bold blue]{dir_name}/[/]", None, False))

        # Files in directory
        for file_idx, (display_name, full_path) in enumerate(files):
            is_last_file = file_idx == len(files) - 1
            prefix = "└── " if is_last_file else "├── "
            result.append((f"[dim]{prefix}[/]{display_name}", full_path, is_last_file and is_last_dir))

    return result


def _show_evolution_matrix(
    transitions: list[tuple[VersionInfo, VersionInfo]],
    matrix: dict[str, list[tuple[str, any]]],
):
    """
    Display evolution as a compact matrix with tree-style file column.
    """
    from rich.table import Table

    # Build tree structure for file paths
    tree_rows = _build_tree_structure(list(matrix.keys()))

    # Build table
    table = Table(show_header=True, header_style="dim", box=None, padding=(0, 1))

    # File column (wider for tree)
    table.add_column("", style="bold", no_wrap=True)

    # Transition columns
    for left, right in transitions:
        table.add_column(f"{left.id}→{right.id}", justify="center", no_wrap=True)

    # Add rows
    for display_name, full_path, _ in tree_rows:
        if full_path is None:
            # Directory header row - no data columns
            row = [display_name] + [""] * len(transitions)
        else:
            # File row with change data
            changes = matrix[full_path]
            row = [display_name]
            for _, change in changes:
                if change is None:
                    cell = "[dim]·[/]"
                elif change == "+":
                    cell = "[green bold]+new[/]"
                elif change == "-":
                    cell = "[red bold]−del[/]"
                else:
                    ins, dels = change
                    # Compact representation
                    if ins > 0 and dels > 0:
                        cell = f"[yellow]+{ins}/-{dels}[/]"
                    elif ins > 0:
                        cell = f"[green]+{ins}[/]"
                    else:
                        cell = f"[red]-{dels}[/]"
                row.append(cell)
        table.add_row(*row)

    console.print(table)

    # Summary
    total_files = len(matrix)
    console.print()
    console.print(f"[dim]{total_files} files with changes across {len(transitions)} transitions[/]")


def _show_evolution_outline(
    versions: list[VersionInfo],
    matrix: dict[str, list[tuple[str, any]]],
    routes_only: bool = False,
):
    """
    Display evolution with function-level detail, grouped by version transition.
    """
    for i in range(len(versions) - 1):
        left = versions[i]
        right = versions[i + 1]

        # Collect files that changed in this transition
        changed_files = []
        for rel_path, changes in matrix.items():
            if not rel_path.endswith(".py"):
                continue
            change = changes[i][1]
            if change is not None:
                changed_files.append((rel_path, change))

        if not changed_files:
            continue

        console.print(f"[bold cyan]{left.id}[/] → [bold cyan]{right.id}[/]")

        for rel_path, change in sorted(changed_files):
            if change == "+":
                # New file: show all functions
                funcs = extract_functions_from_file(right.path / rel_path)
                if routes_only:
                    funcs = {k: v for k, v in funcs.items() if v.route}
                if funcs:
                    console.print(f"  [green]+[/] [bold]{rel_path}[/]")
                    for name, info in funcs.items():
                        route_str = f" [cyan]{info.route}[/]" if info.route else ""
                        console.print(f"      [green]+[/] {name}(){route_str}")
            elif change == "-":
                # Deleted file
                funcs = extract_functions_from_file(left.path / rel_path)
                if routes_only:
                    funcs = {k: v for k, v in funcs.items() if v.route}
                if funcs:
                    console.print(f"  [red]−[/] [bold]{rel_path}[/]")
                    for name, info in funcs.items():
                        route_str = f" [cyan]{info.route}[/]" if info.route else ""
                        console.print(f"      [red]−[/] {name}(){route_str}")
            else:
                # Modified file: show function changes
                func_changes = calculate_function_changes(left.path, right.path, rel_path)
                if routes_only:
                    func_changes = [c for c in func_changes if c.route]
                if func_changes:
                    console.print(f"  [yellow]~[/] [bold]{rel_path}[/]")
                    for fc in func_changes:
                        route_str = f" [cyan]{fc.route}[/]" if fc.route else ""
                        if fc.change_type == "added":
                            console.print(f"      [green]+[/] {fc.name}(){route_str}")
                        elif fc.change_type == "deleted":
                            console.print(f"      [red]−[/] {fc.name}(){route_str}")
                        else:
                            line_info = ""
                            if fc.old_lines and fc.new_lines and fc.old_lines != fc.new_lines:
                                line_info = f" [dim]{fc.old_lines}→{fc.new_lines} lines[/]"
                            console.print(f"      [yellow]~[/] {fc.name}(){route_str}{line_info}")

        console.print()


def show_outline(
    result: DiffResult,
    file_filter: str | None = None,
    routes_only: bool = False,
) -> None:
    """
    Show function/route-level outline of changes.

    For each changed Python file, shows which functions were added/modified/deleted.
    For files in routes/ directories, also shows the affected route paths.

    Args:
        result: The diff result to display
        file_filter: Optional pattern to filter files
        routes_only: If True, only show files with route decorators
    """
    console.print()
    console.print(f"[bold cyan]{result.left.id}[/] -> [bold cyan]{result.right.id}[/]  [dim](function outline)[/]")
    console.print()

    # Get all Python files that changed
    py_files = []
    for filepath in result.added + result.modified + result.deleted:
        if filepath.endswith(".py") and (not file_filter or file_filter in filepath):
            py_files.append(filepath)

    if not py_files:
        console.print("[dim]No Python files changed[/]")
        return

    files_with_changes = 0
    total_added = 0
    total_modified = 0
    total_deleted = 0

    for filepath in sorted(py_files):
        # Determine change status of the file itself
        if filepath in result.added:
            file_status = "A"
            file_style = "green"
        elif filepath in result.deleted:
            file_status = "D"
            file_style = "red"
        else:
            file_status = "M"
            file_style = "yellow"

        # Calculate function-level changes
        if file_status == "A":
            # New file: all functions are added
            funcs = extract_functions_from_file(result.right.path / filepath)
            changes = [
                FunctionChange(name=name, change_type="added", route=info.route, new_lines=info.line_count)
                for name, info in funcs.items()
            ]
        elif file_status == "D":
            # Deleted file: all functions are deleted
            funcs = extract_functions_from_file(result.left.path / filepath)
            changes = [
                FunctionChange(name=name, change_type="deleted", route=info.route, old_lines=info.line_count)
                for name, info in funcs.items()
            ]
        else:
            # Modified file: calculate detailed function changes
            changes = calculate_function_changes(result.left.path, result.right.path, filepath)

        # Filter to routes only if requested
        if routes_only:
            changes = [c for c in changes if c.route]

        if not changes:
            continue

        files_with_changes += 1

        # Print file header
        console.print(f"[{file_style}]{file_status}[/{file_style}] [bold]{filepath}[/]")

        # Group and print function changes
        added = [c for c in changes if c.change_type == "added"]
        modified = [c for c in changes if c.change_type == "modified"]
        deleted = [c for c in changes if c.change_type == "deleted"]

        total_added += len(added)
        total_modified += len(modified)
        total_deleted += len(deleted)

        def format_func_change(change: FunctionChange) -> str:
            """Format a single function change for display."""
            parts = [f"{change.name}()"]

            # Add route if present (especially useful for routes files)
            if change.route:
                parts.append(f"[cyan]{change.route}[/cyan]")

            # Add line count info for non-trivial changes
            if change.change_type == "modified":
                if change.old_lines != change.new_lines:
                    parts.append(f"[dim]{change.old_lines} → {change.new_lines} lines[/dim]")
            elif change.change_type == "added" and change.new_lines > 0:
                parts.append(f"[dim]{change.new_lines} lines[/dim]")
            elif change.change_type == "deleted" and change.old_lines > 0:
                parts.append(f"[dim]{change.old_lines} lines[/dim]")

            return " ".join(parts)

        if added:
            for change in sorted(added, key=lambda c: c.name):
                console.print(f"    [green]+[/green] {format_func_change(change)}")

        if modified:
            for change in sorted(modified, key=lambda c: c.name):
                console.print(f"    [yellow]~[/yellow] {format_func_change(change)}")

        if deleted:
            for change in sorted(deleted, key=lambda c: c.name):
                console.print(f"    [red]-[/red] {format_func_change(change)}")

        console.print()

    # Summary
    if files_with_changes > 0:
        console.print(
            f"[dim]Summary:[/] {files_with_changes} files, "
            f"[green]+{total_added}[/green] added, "
            f"[yellow]~{total_modified}[/yellow] modified, "
            f"[red]-{total_deleted}[/red] deleted functions"
        )
    else:
        console.print("[dim]No function-level changes detected in Python files[/]")


def show_routes(result: DiffResult, file_filter: str | None = None) -> None:
    """
    Show only route-level changes (functions with @bp.route decorators).

    This is a convenience wrapper around show_outline with routes_only=True.
    """
    show_outline(result, file_filter=file_filter, routes_only=True)


# =============================================================================
# Main
# =============================================================================


def apply_change_type_filter(result: DiffResult, args: argparse.Namespace) -> None:
    """Apply --added-only, --modified-only, --deleted-only filters."""
    if args.added_only:
        result.modified = []
        result.deleted = []
    elif args.modified_only:
        result.added = []
        result.deleted = []
    elif args.deleted_only:
        result.added = []
        result.modified = []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare exercise versions in Unsafe Code Lab",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ucdiff v307                     Tree view (auto-compare with v306)
  ucdiff v307 -o                  Function-level changes
  ucdiff v307 -r                  Route-level changes only
  ucdiff v307 -c                  Syntax-aware code diff
  ucdiff v307 -cS                 Code diff, side-by-side
  ucdiff v307 -cF                 Code diff, focused (max noise reduction)
  ucdiff v307 -c --tool delta     Word-level highlighting
  ucdiff v307 -l                  Just list changed files
  ucdiff r03                      Overview of all section changes
  ucdiff r03 -e orders.py         Evolution of orders.py (partial match)
  ucdiff r03 -e routes/           Evolution of all routes/ files
  ucdiff v307 --json              Machine-readable output
""",
    )

    parser.add_argument("versions", nargs="*", help="Versions to compare")

    # Primary output flags (new simplified interface)
    primary_group = parser.add_argument_group("Primary output flags")
    primary_group.add_argument("-c", "--code", action="store_true",
                               help="Show code changes (syntax-aware via difftastic)")
    primary_group.add_argument("-l", "--list", action="store_true",
                               help="Just filenames (for scripting)")
    primary_group.add_argument("-o", "--outline", action="store_true",
                               help="Show function-level changes (added/modified/deleted)")
    primary_group.add_argument("-r", "--routes", action="store_true",
                               help="Show only route-level changes (functions with @bp.route)")
    primary_group.add_argument("--json", action="store_true",
                               help="Machine-readable JSON output")

    # Display options
    display_group = parser.add_argument_group("Display options")
    display_group.add_argument("-S", "--side", action="store_true",
                               help="Side-by-side view for --code mode")
    display_group.add_argument("--tool", choices=["difft", "delta", "icdiff"], default="difft",
                               help="Diff tool for --code mode (default: difft)")
    display_group.add_argument("--ignore-comments", "--no-comments", action="store_true",
                               help="Ignore comment changes (difftastic only)")
    display_group.add_argument("-F", "--focused", "--focus", action="store_true",
                               help="Maximum noise reduction (--ignore-comments + context=1)")
    display_group.add_argument("-b", "--boring", action="store_true",
                               help="Show boring files at full brightness")

    # Backward compatibility (hidden from help but still functional)
    compat_group = parser.add_argument_group("Legacy options (deprecated)")
    compat_group.add_argument(
        "-m", "--mode",
        choices=["tree", "summary", "stat", "files", "unified", "side", "syntax", "delta", "json"],
        default="tree",
        help=argparse.SUPPRESS,  # Hidden from help
    )
    compat_group.add_argument("-t", "--tree-mode", action="store_true",
                              help=argparse.SUPPRESS)
    compat_group.add_argument("-q", "--quick", action="store_true",
                              help="Quick summary (compact table + --no-wiring)")
    compat_group.add_argument("-s", "--stat-mode", action="store_true",
                              help=argparse.SUPPRESS)
    compat_group.add_argument("-u", "--unified-mode", action="store_true",
                              help=argparse.SUPPRESS)
    compat_group.add_argument("--syntax", action="store_true",
                              help=argparse.SUPPRESS)

    # Filters
    filter_group = parser.add_argument_group("Filters")
    filter_group.add_argument("-f", "--file", help="Only files matching pattern")
    filter_group.add_argument("--exclude", help="Exclude files matching pattern")
    filter_group.add_argument("--no-wiring", action="store_true",
                              help="Skip config.py and routes/__init__.py")
    filter_group.add_argument("--only-code", action="store_true",
                              help="Only Python code, exclude fixtures/models")
    filter_group.add_argument("--added-only", action="store_true",
                              help="Only show added files")
    filter_group.add_argument("--modified-only", action="store_true",
                              help="Only show modified files")
    filter_group.add_argument("--deleted-only", action="store_true",
                              help="Only show deleted files")

    # Diff options
    diff_group = parser.add_argument_group("Diff options")
    diff_group.add_argument("-U", "--context", type=int, default=3,
                            help="Number of context lines for diff (default: 3)")
    diff_group.add_argument("--check-specs", action="store_true",
                            help="Warn when code changes but specs don't")
    diff_group.add_argument("--no-hints", action="store_true",
                            help="Disable integration hints")

    # Evolution mode
    parser.add_argument("-e", "--evolution", nargs="?", const="", metavar="FILE",
                        help="Show file evolution across versions (optional file pattern)")

    args = parser.parse_args()

    # Validate we have something to work with
    if not args.versions:
        parser.print_help()
        sys.exit(0)

    try:
        # Handle evolution mode (triggered by -e flag, with or without file pattern)
        if args.evolution is not None:  # -e was used (could be "" for no pattern)
            if len(args.versions) == 1:
                version_str = args.versions[0]
                if SECTION_RE.match(version_str):
                    versions = list_section_versions(version_str)
                elif ".." in version_str:
                    left, right = version_str.split("..")
                    versions = get_version_range(left, right)
                else:
                    raise ValueError("Evolution mode needs section (r03) or range (v301..v307)")
            elif len(args.versions) == 2:
                versions = get_version_range(args.versions[0], args.versions[1])
            else:
                raise ValueError("Evolution mode needs section or version range")

            # File pattern: None if empty string (show all), otherwise the pattern
            file_pattern = args.evolution if args.evolution else None

            # Support combining with -o (outline) and -r (routes)
            show_evolution(
                versions,
                file_pattern=file_pattern,
                outline_mode=args.outline or args.routes,
                routes_only=args.routes,
            )
            return

        # Parse version specifications
        if len(args.versions) == 1:
            version_str = args.versions[0]

            # Check for range syntax: v301..v307
            if ".." in version_str:
                left_str, right_str = version_str.split("..")
                left = resolve_version(left_str)
                right = resolve_version(right_str)
            # Check for section: r03
            elif SECTION_RE.match(version_str):
                versions = list_section_versions(version_str)

                # Handle --focused meta-flag (maximum noise reduction)
                context_lines = args.context
                ignore_comments = args.ignore_comments
                if args.focused:
                    ignore_comments = True
                    context_lines = 1

                for i in range(len(versions) - 1):
                    result = compare_directories(
                        versions[i], versions[i + 1],
                        file_filter=args.file,
                        exclude_pattern=args.exclude,
                        no_wiring=args.no_wiring or args.quick,
                        only_code=args.only_code,
                    )
                    # Apply change type filters
                    apply_change_type_filter(result, args)
                    if args.check_specs:
                        result.spec_drift = detect_spec_drift(result)
                    # Determine output mode for section loop
                    if args.code:
                        difft_display = "side-by-side" if args.side else "inline"
                        # Route to appropriate tool
                        if args.tool == "difft":
                            show_syntax_diff(
                                result, args.file, context_lines,
                                display=difft_display, ignore_comments=ignore_comments
                            )
                        elif args.tool == "delta":
                            show_delta(result, args.file, context_lines, side_by_side=True)
                        elif args.tool == "icdiff":
                            show_side_by_side(result, args.file, context_lines)
                    elif args.outline:
                        show_outline(result, file_filter=args.file)
                    elif args.routes:
                        show_routes(result, file_filter=args.file)
                    elif args.list:
                        show_files(result)
                    elif args.json:
                        show_json(result)
                    elif args.quick:
                        show_summary(
                            result,
                            check_specs=args.check_specs,
                            show_hints=not args.no_hints,
                        )
                    else:
                        show_tree(
                            result,
                            check_specs=args.check_specs,
                            show_hints=not args.no_hints,
                            highlight_boring=args.boring,
                        )
                return
            # Auto-prev: single version like v307 -> compare with v306
            elif VERSION_RE.match(version_str):
                prev_version = get_previous_version(version_str)
                if not prev_version:
                    raise ValueError(
                        f"Cannot auto-detect previous version for {version_str}. "
                        f"This is the first exercise in the section. "
                        f"Specify both versions: ucdiff <from> {version_str}"
                    )
                # Verify the previous version exists
                try:
                    left = resolve_version(prev_version)
                except ValueError:
                    raise ValueError(
                        f"Previous version {prev_version} does not exist. "
                        f"Specify both versions explicitly."
                    ) from None
                right = resolve_version(version_str)
            else:
                raise ValueError("Need two versions or a range (v301..v307)")
        elif len(args.versions) == 2:
            left = resolve_version(args.versions[0])
            right = resolve_version(args.versions[1])
        else:
            raise ValueError("Too many arguments")

        # Compare the directories
        result = compare_directories(
            left, right,
            file_filter=args.file,
            exclude_pattern=args.exclude,
            no_wiring=args.no_wiring or args.quick,
            only_code=args.only_code,
        )

        # Apply change type filters (--added-only, etc.)
        apply_change_type_filter(result, args)

        # Detect spec drift if requested
        if args.check_specs:
            result.spec_drift = detect_spec_drift(result)

        # Determine output mode - new flags take priority
        mode = args.mode
        side_by_side = args.side  # -S/--side flag
        tool = args.tool  # 'difft', 'delta', or 'icdiff'
        ignore_comments = args.ignore_comments

        # Handle --focused meta-flag (maximum noise reduction)
        if args.focused:
            ignore_comments = True
            args.context = 1  # Minimal context

        # New primary flags
        if args.code:
            mode = "code"
        elif args.outline:
            mode = "outline"
        elif args.routes:
            mode = "routes"
        elif args.list:
            mode = "list"
        elif args.json:
            mode = "json"
        # Legacy presets (backward compat)
        elif args.tree_mode:
            mode = "tree"
        elif args.quick:
            mode = "summary"
        elif args.stat_mode:
            mode = "stat"
        elif args.unified_mode:
            mode = "unified"
        elif args.syntax:
            mode = "code"  # Legacy --syntax maps to code mode
            tool = "difft"
        # Handle deprecated -m mode values - now preserve tool value
        elif args.mode == "side":
            # Redirect to code with icdiff (traditional side-by-side)
            mode = "code"
            tool = "icdiff"
        elif args.mode == "syntax":
            mode = "code"
            tool = "difft"
        elif args.mode == "files":
            mode = "list"
        elif args.mode in ("summary", "stat"):
            # Redirect summary/stat to tree with message
            console.print(f"[dim]Note: --mode {args.mode} is deprecated, using tree view[/]")
            mode = "tree"
        elif args.mode == "delta":
            # Redirect delta to code with delta tool (preserves unique value)
            mode = "code"
            tool = "delta"

        context_lines = args.context
        highlight_boring = args.boring

        # Map side flag to difftastic display format
        difft_display = "side-by-side" if side_by_side else "inline"

        # Output based on mode
        if mode == "tree":
            show_tree(
                result,
                check_specs=args.check_specs,
                show_hints=not args.no_hints,
                highlight_boring=highlight_boring,
            )
        elif mode == "summary":
            show_summary(result, check_specs=args.check_specs, show_hints=not args.no_hints)
        elif mode == "stat":
            show_stat(result)
        elif mode == "outline":
            show_outline(result, file_filter=args.file)
        elif mode == "routes":
            show_routes(result, file_filter=args.file)
        elif mode == "list":
            show_files(result)
        elif mode == "unified":
            show_unified(result, args.file, context_lines)
        elif mode == "side":
            show_side_by_side(result, args.file, context_lines)
        elif mode == "code" or mode == "syntax":
            # Route to appropriate tool
            if tool == "difft":
                show_syntax_diff(
                    result, args.file, context_lines,
                    display=difft_display, ignore_comments=ignore_comments
                )
            elif tool == "delta":
                show_delta(result, args.file, context_lines, side_by_side=True)
            elif tool == "icdiff":
                show_side_by_side(result, args.file, context_lines)
        elif mode == "delta":
            show_delta(result, args.file, context_lines, side_by_side=True)
        elif mode == "json":
            show_json(result)

        # Always exit 0 for successful display (this is a visualization tool, not a test)
        sys.exit(0)

    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(2)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted[/]")
        sys.exit(130)


if __name__ == "__main__":
    main()
