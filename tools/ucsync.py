#!/usr/bin/env python3
"""
ucspec - E2E spec suite generator for inherited test files

Reads spec.yml and generates inherited test files for nested directory structures.
Only new/override specs are stored in git; inherited files are generated on-demand.

Design principles:
- Nested structure: endpoint-first layout (resource/action/verb/*.http)
- Implicit inheritance: Versions inherit entire directory tree from parent
- File-based inheritance: ~filename.http prefix marks inherited files
- Override by position: New files in same path override inherited ones
- Idempotent: Running multiple times is safe

File naming:
- New/Override specs: {name}.http (stored in git)
- Inherited: ~{name}.http (generated, tracked in git for httpyac compatibility)

Usage:
  ucspec                    # Generate inherited files + sync tags (all versions)
  ucspec v302               # Generate for specific version
  ucspec --dry-run          # Preview changes
  ucspec clean              # Remove all inherited files
"""

import argparse
import contextlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Inherited file prefix - files starting with this are generated
INHERITED_PREFIX = "~"

# Files/directories to skip during inheritance
SKIP_PATTERNS = {".env", "__pycache__", ".DS_Store", ".git"}

# Infrastructure files - copied without prefix (not test content)
INFRASTRUCTURE_PATTERNS = {"_imports.http", "_fixtures.http"}

# Detect HTTP request boundaries
HTTP_METHOD_PATTERN = re.compile(
    r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+", re.IGNORECASE
)


@dataclass
class VersionSpec:
    """Resolved specification for a version"""

    name: str
    description: str
    tags: list[str]
    tag_rules: dict[str, list[str]]  # Pattern -> additional tags
    inherits_from: str | None
    exclude: set[str]  # Relative paths to exclude from inheritance


@dataclass
class SyncResult:
    """Result of a sync operation"""

    generated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class UcspecError(Exception):
    """Base exception for ucspec errors"""

    pass


# =============================================================================
# Configuration Loading
# =============================================================================


def load_spec_config(spec_yml_path: Path) -> dict:
    """Load and validate spec.yml"""
    with open(spec_yml_path) as f:
        config = yaml.safe_load(f)

    if not config:
        raise UcspecError("spec.yml is empty")

    return config


def resolve_version(version_name: str, config: dict) -> VersionSpec:
    """Resolve a version's configuration from spec.yml"""
    if version_name not in config:
        raise UcspecError(f"Version '{version_name}' not found in spec.yml")

    version_config = config[version_name]

    return VersionSpec(
        name=version_name,
        description=version_config.get("description", ""),
        tags=version_config.get("tags", []),
        tag_rules=version_config.get("tag_rules", {}),
        inherits_from=version_config.get("inherits"),
        exclude=set(version_config.get("exclude", [])),
    )


def get_inherited_tag_rules(
    version: VersionSpec, config: dict, resolved_cache: dict[str, VersionSpec]
) -> dict[str, list[str]]:
    """Get tag_rules including inherited ones from parent versions."""
    rules = {}

    # First, get parent's rules (if any)
    if version.inherits_from:
        if version.inherits_from not in resolved_cache:
            parent = resolve_version(version.inherits_from, config)
            resolved_cache[version.inherits_from] = parent
        else:
            parent = resolved_cache[version.inherits_from]

        # Recursively get parent's rules
        parent_rules = get_inherited_tag_rules(parent, config, resolved_cache)
        rules.update(parent_rules)

    # Then apply this version's rules (can override parent patterns)
    rules.update(version.tag_rules)

    return rules


# =============================================================================
# Pattern Matching
# =============================================================================


def matches_glob_pattern(path: str, pattern: str) -> bool:
    """Match a path against a glob-like pattern.

    Supports:
    - * matches any single path component (not /)
    - ** matches any number of path components
    - ? matches single character

    Examples:
        "auth/**" matches "auth/login/post/happy.http"
        "**/authn.http" matches "any/path/authn.http"
        "orders/refund/**" matches "orders/refund/status/get/happy.http"
    """
    # Normalize path separators
    path = path.replace("\\", "/")

    # Convert glob pattern to regex
    # Split on ** first to handle it specially
    parts = pattern.split("**")

    regex_parts = []
    for i, part in enumerate(parts):
        if part:
            # Convert single * to match non-slash characters
            # Convert ? to match single non-slash character
            escaped = re.escape(part)
            escaped = escaped.replace(r"\*", r"[^/]*")
            escaped = escaped.replace(r"\?", r"[^/]")
            regex_parts.append(escaped)

        # Add .* for ** (matches anything including /)
        if i < len(parts) - 1:
            regex_parts.append(r".*")

    regex = "^" + "".join(regex_parts) + "$"

    return bool(re.match(regex, path))


# =============================================================================
# File Utilities
# =============================================================================


def is_infrastructure_file(filename: str) -> bool:
    """Check if a file is an infrastructure file (copied without prefix)"""
    return filename in INFRASTRUCTURE_PATTERNS or filename.startswith("_")


def get_inherited_filename(filename: str) -> str:
    """Convert a filename to its inherited form (~prefix for tests, as-is for infrastructure)"""
    if is_infrastructure_file(filename):
        return filename  # Infrastructure files keep original name
    return f"{INHERITED_PREFIX}{filename}"


def is_inherited_file(path: Path) -> bool:
    """Check if a file is an inherited file (has ~ prefix, not infrastructure)"""
    return path.name.startswith(INHERITED_PREFIX) and not is_infrastructure_file(path.name)


def get_original_filename(inherited_name: str) -> str:
    """Get the original filename from an inherited filename"""
    if inherited_name.startswith(INHERITED_PREFIX):
        return inherited_name[len(INHERITED_PREFIX) :]
    return inherited_name


def should_skip(path: Path) -> bool:
    """Check if a path should be skipped during processing"""
    return path.name in SKIP_PATTERNS or path.name.startswith(".")


# =============================================================================
# File Scanning
# =============================================================================


def scan_source_files(source_dir: Path) -> dict[str, Path]:
    """
    Scan source directory for all .http files.
    Returns dict of relative_path -> absolute_path
    """
    files = {}

    if not source_dir.exists():
        return files

    for path in source_dir.rglob("*.http"):
        if should_skip(path) or is_inherited_file(path):
            continue

        rel_path = path.relative_to(source_dir)
        files[str(rel_path)] = path

    return files


def scan_new_files(target_dir: Path, include_infrastructure: bool = True) -> set[str]:
    """
    Scan target directory for new (non-inherited) .http files.
    Returns set of relative paths.
    """
    files = set()

    if not target_dir.exists():
        return files

    for path in target_dir.rglob("*.http"):
        if should_skip(path) or is_inherited_file(path):
            continue

        # Optionally skip infrastructure files
        if not include_infrastructure and is_infrastructure_file(path.name):
            continue

        rel_path = path.relative_to(target_dir)
        files.add(str(rel_path))

    return files


def scan_inherited_files(target_dir: Path, new_files: set[str] | None = None) -> dict[str, Path]:
    """
    Scan target directory for inherited files.
    Includes both ~prefixed test files and infrastructure files (without prefix).

    Returns dict of original_relative_path -> inherited_file_path
    """
    files = {}
    new_files = new_files or set()

    if not target_dir.exists():
        return files

    # Scan for ~prefixed test files
    for path in target_dir.rglob(f"{INHERITED_PREFIX}*.http"):
        if should_skip(path):
            continue

        # Get original path (without ~ prefix)
        parent = path.parent.relative_to(target_dir)
        original_name = get_original_filename(path.name)
        original_rel_path = str(parent / original_name)

        files[original_rel_path] = path

    # Scan for infrastructure files (these don't have ~ prefix but are inherited)
    for path in target_dir.rglob("_*.http"):
        if should_skip(path):
            continue

        rel_path = str(path.relative_to(target_dir))

        # Skip if this is a "new" file (git-tracked override)
        if rel_path in new_files:
            continue

        files[rel_path] = path

    return files


# =============================================================================
# Import Rewriting
# =============================================================================


def rewrite_imports_for_inheritance(
    content: str,
    source_files: dict[str, Path],
    current_file_rel_path: str,
    child_overrides: set[str] | None = None,
    child_excludes: set[str] | None = None,
) -> str:
    """
    Rewrite @import statements in inherited content for proper ~ prefix handling.

    This function handles both directions of import rewriting:

    1. ADDING ~ prefix: When inheriting a file that imports a sibling file,
       the import path is updated to reference the inherited version.
       - @import ./happy.http -> @import ./~happy.http

    2. REMOVING ~ prefix: When the child version has a local override of the
       imported file, the ~ prefix is stripped so the import references the
       local version instead of a non-existent ~ version.
       - @import ./~happy.http -> @import ./happy.http (if child has override)

    Cases that are NOT rewritten:
    - Infrastructure files: @import ../_imports.http (keep their names)
    - Files outside version directory: @import ../../../common.http
    - Files not in source: safe fallback to avoid breaking imports

    Override-aware rewriting ensures inherited files correctly reference local
    overrides or excluded files instead of non-existent ~ versions.
    """
    current_dir = Path(current_file_rel_path).parent
    child_overrides = child_overrides or set()
    child_excludes = child_excludes or set()

    def rewrite_import(match: re.Match) -> str:
        prefix = match.group(1)  # "# @import " or similar
        import_path = match.group(2)  # The path being imported

        # Parse the path to get the filename
        path_obj = Path(import_path)
        filename = path_obj.name

        # Don't rewrite infrastructure files
        # Note: We check the base filename (without ~) for infrastructure check
        base_filename = get_original_filename(filename) if filename.startswith(INHERITED_PREFIX) else filename
        if is_infrastructure_file(base_filename):
            return match.group(0)

        # Check if this looks like a .http file import
        if not filename.endswith(".http"):
            return match.group(0)

        # Determine if import already has ~ prefix
        has_prefix = filename.startswith(INHERITED_PREFIX)

        # Resolve the import path relative to current file's directory
        # Use the ORIGINAL filename (without ~) for path resolution
        original_filename = get_original_filename(filename) if has_prefix else filename
        original_path_obj = path_obj.parent / original_filename if has_prefix else path_obj

        try:
            resolved_path = (current_dir / original_path_obj).as_posix()
            # Normalize the path (remove ./ and resolve ../)
            parts = []
            goes_outside = False
            for part in resolved_path.split("/"):
                if part == "..":
                    if parts:
                        parts.pop()
                    else:
                        # Path goes outside the version directory, don't rewrite
                        goes_outside = True
                        break
                elif part and part != ".":
                    parts.append(part)

            if goes_outside:
                return match.group(0)

            normalized_path = "/".join(parts)

            # Check if child has a local override for this file or it's excluded
            has_local_override = (
                normalized_path in child_overrides
                or is_excluded(normalized_path, child_excludes)
            )

            if has_local_override:
                # Child has override -> import should NOT have ~ prefix
                if has_prefix:
                    # Remove ~ prefix: ~happy.http -> happy.http
                    new_path = str(path_obj.parent / original_filename) if path_obj.parent != Path(".") else original_filename
                    return f"{prefix}{new_path}"
                else:
                    # Already no prefix, keep as-is
                    return match.group(0)
            else:
                # No override -> import should have ~ prefix
                # But first check if the file exists in source_files
                if normalized_path not in source_files:
                    return match.group(0)

                if has_prefix:
                    # Already has prefix, keep as-is
                    return match.group(0)
                else:
                    # Add ~ prefix: happy.http -> ~happy.http
                    new_filename = get_inherited_filename(filename)
                    new_path = str(path_obj.parent / new_filename) if path_obj.parent != Path(".") else new_filename
                    return f"{prefix}{new_path}"

        except (ValueError, IndexError):
            # If path resolution fails, don't rewrite
            return match.group(0)

    # Match @import statements: # @import <path>
    pattern = r"(#\s*@import\s+)(\S+\.http)"
    return re.sub(pattern, rewrite_import, content)


# =============================================================================
# Tag Syncing (Simplified - no leaf-node optimization)
# =============================================================================


def compute_file_tags(
    rel_path: str, version_tags: list[str], tag_rules: dict[str, list[str]]
) -> list[str]:
    """Compute all tags that apply to a file based on version tags and pattern rules."""
    # Start with version-level tags
    tags = set(version_tags)

    # Strip ~ prefix for pattern matching
    pattern_path = rel_path
    filename = Path(rel_path).name
    if filename.startswith(INHERITED_PREFIX):
        original_name = get_original_filename(filename)
        pattern_path = str(Path(rel_path).parent / original_name)

    # Add pattern-matched tags
    for pattern, pattern_tags in tag_rules.items():
        if matches_glob_pattern(pattern_path, pattern):
            tags.update(pattern_tags)

    return sorted(tags)


def sync_file_tags(file_path: Path, tags: list[str], dry_run: bool = False) -> tuple[bool, str | None]:
    """Sync tags in a single .http file - apply same tags to all requests.

    Returns:
        Tuple of (changed: bool, error: str | None)
    """
    try:
        content = file_path.read_text()
    except (OSError, UnicodeDecodeError) as e:
        return False, f"Failed to read {file_path}: {e}"

    # Remove all existing @tag lines
    new_content = re.sub(r"^#\s*@tag\s+.*\n", "", content, flags=re.MULTILINE)

    # Insert @tag before each HTTP method line
    if tags:
        tag_line = f"# @tag {', '.join(tags)}\n"
        lines = new_content.split("\n")
        result_lines = []
        for line in lines:
            if HTTP_METHOD_PATTERN.match(line):
                result_lines.append(tag_line.rstrip())
            result_lines.append(line)
        new_content = "\n".join(result_lines)

    if content == new_content:
        return False, None  # No changes needed

    if not dry_run:
        try:
            file_path.write_text(new_content)
        except OSError as e:
            return False, f"Failed to write {file_path}: {e}"

    return True, None


def sync_version_tags(
    version: VersionSpec,
    spec_dir: Path,
    config: dict,
    resolved_cache: dict[str, VersionSpec],
    dry_run: bool = False,
) -> SyncResult:
    """Sync tags for all .http files in a version directory.

    Tags are computed from:
    1. Version-level tags (from spec.yml)
    2. Pattern-based tag_rules (inherited from parent + own rules)

    All matching tags are applied to all requests in matching files.
    (uctest handles any deduplication at runtime)
    """
    result = SyncResult()
    version_dir = spec_dir / version.name

    if not version_dir.exists():
        return result

    # Get effective tag rules (including inherited)
    tag_rules = get_inherited_tag_rules(version, config, resolved_cache)

    # Process each .http file
    for http_file in version_dir.rglob("*.http"):
        if is_infrastructure_file(http_file.name) or should_skip(http_file):
            continue

        rel_path = str(http_file.relative_to(version_dir))

        # Compute tags for this file
        tags = compute_file_tags(rel_path, version.tags, tag_rules)

        # Sync tags to file
        changed, error = sync_file_tags(http_file, tags, dry_run=dry_run)

        if error:
            result.errors.append(error)
        elif changed:
            result.generated.append(f"{version.name}/{rel_path}")

    return result


# =============================================================================
# File Generation
# =============================================================================


def normalize_exclude_path(path: str) -> str:
    """Normalize an exclude path for comparison"""
    return path.strip("/").replace("\\", "/")


def is_excluded(rel_path: str, exclude_set: set[str]) -> bool:
    """Check if a relative path matches any exclude pattern"""
    normalized = normalize_exclude_path(rel_path)

    for exclude in exclude_set:
        exclude_norm = normalize_exclude_path(exclude)

        # Exact match
        if normalized == exclude_norm:
            return True

        # Directory prefix match (exclude entire subtree)
        if normalized.startswith(exclude_norm + "/"):
            return True

    return False


def generate_version(
    version: VersionSpec,
    spec_dir: Path,
    resolved_cache: dict[str, VersionSpec],
    dry_run: bool = False,
) -> SyncResult:
    """Generate inherited files for a version with nested structure"""
    result = SyncResult()
    target_dir = spec_dir / version.name

    # Ensure version directory exists
    if not target_dir.exists():
        if dry_run:
            result.warnings.append(f"Would create directory: {target_dir}")
        else:
            target_dir.mkdir(parents=True)

    # Create/update .env file
    env_file = target_dir / ".env"
    env_content = f"VERSION={version.name}\n"
    if not env_file.exists() or env_file.read_text() != env_content:
        if dry_run:
            result.generated.append(f"{version.name}/.env")
        else:
            env_file.write_text(env_content)
            result.generated.append(f"{version.name}/.env")

    # If no inheritance, nothing more to do
    if not version.inherits_from:
        # For base versions, only clean ~prefixed files (not infrastructure)
        for path in target_dir.rglob(f"{INHERITED_PREFIX}*.http"):
            if should_skip(path):
                continue
            if dry_run:
                result.removed.append(str(path.relative_to(spec_dir)))
            else:
                path.unlink()
                result.removed.append(str(path.relative_to(spec_dir)))
        return result

    # Resolve parent version
    if version.inherits_from not in resolved_cache:
        parent_spec = resolve_version(
            version.inherits_from, load_spec_config(spec_dir / "spec.yml")
        )
        resolved_cache[version.inherits_from] = parent_spec

    source_dir = spec_dir / version.inherits_from

    # Get all source files from parent
    source_files = scan_source_files(source_dir)

    # Also include inherited files from parent (recursive inheritance)
    parent_inherited = scan_inherited_files(source_dir)
    for rel_path, inherited_path in parent_inherited.items():
        if rel_path not in source_files:
            source_files[rel_path] = inherited_path

    # Get new files in target (these override inherited)
    new_files = scan_new_files(target_dir)

    # Warn about unacknowledged overrides (local files that shadow inherited files)
    # User can silence by adding to 'exclude:' in spec.yml
    for override_path in new_files:
        if override_path in source_files and not is_excluded(override_path, version.exclude):
            # Skip infrastructure files - they're expected to be overridden
            if not is_infrastructure_file(Path(override_path).name):
                result.warnings.append(
                    f"Local override '{override_path}' shadows inherited file. "
                    f"Add to 'exclude:' in spec.yml to acknowledge."
                )

    # Get existing inherited files in target
    existing_inherited = scan_inherited_files(target_dir, new_files)

    # Track which inherited files we expect to have
    expected_inherited: set[str] = set()

    for rel_path, source_path in source_files.items():
        # Skip if excluded
        if is_excluded(rel_path, version.exclude):
            continue

        # Skip if target has a new (override) file at this path
        if rel_path in new_files:
            continue

        expected_inherited.add(rel_path)

        # Determine inherited file path
        rel_path_obj = Path(rel_path)
        inherited_name = get_inherited_filename(rel_path_obj.name)
        inherited_rel_path = rel_path_obj.parent / inherited_name
        inherited_path = target_dir / inherited_rel_path

        # Read source content
        source_content = source_path.read_text()

        # Rewrite @import statements to use ~ prefix for inherited sibling files
        # Pass child's local overrides and excludes so imports to overridden files
        # don't get ~ prefix (they should reference the local version instead)
        source_content = rewrite_imports_for_inheritance(
            source_content,
            source_files,
            rel_path,
            child_overrides=new_files,
            child_excludes=version.exclude,
        )

        # Check if we need to write
        needs_write = True
        if inherited_path.exists() and inherited_path.read_text() == source_content:
            needs_write = False

        if needs_write:
            if dry_run:
                result.generated.append(f"{version.name}/{inherited_rel_path}")
            else:
                # Ensure directory exists
                inherited_path.parent.mkdir(parents=True, exist_ok=True)
                inherited_path.write_text(source_content)
                result.generated.append(f"{version.name}/{inherited_rel_path}")

    # Remove orphaned inherited files
    for rel_path, inherited_path in existing_inherited.items():
        if rel_path not in expected_inherited:
            if dry_run:
                result.removed.append(str(inherited_path.relative_to(spec_dir)))
            else:
                inherited_path.unlink()
                result.removed.append(str(inherited_path.relative_to(spec_dir)))

                # Clean up empty directories
                with contextlib.suppress(OSError):
                    inherited_path.parent.rmdir()

    return result


def clean_version(version_dir: Path, dry_run: bool = False) -> SyncResult:
    """Remove all inherited (~prefixed) files from a version directory"""
    result = SyncResult()

    if not version_dir.exists():
        return result

    for path in version_dir.rglob(f"{INHERITED_PREFIX}*.http"):
        if dry_run:
            result.removed.append(str(path.relative_to(version_dir.parent)))
        else:
            path.unlink()
            result.removed.append(str(path.relative_to(version_dir.parent)))

            # Clean up empty directories
            with contextlib.suppress(OSError):
                path.parent.rmdir()

    return result


# =============================================================================
# Path Finding
# =============================================================================


def find_repo_root(start_path: Path | None = None) -> Path | None:
    """Find repo root by looking for pyproject.toml"""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent

    return None


def find_spec_dir(start_path: Path | None = None) -> Path | None:
    """Find the spec directory from anywhere in the repo."""
    if start_path is None:
        start_path = Path.cwd()

    spec_dir = start_path.resolve()

    # Case 1: Already in spec dir with spec.yml
    if (spec_dir / "spec.yml").exists():
        return spec_dir

    # Case 2: In a version subdirectory
    current = spec_dir
    while current != current.parent:
        if (current / "spec.yml").exists():
            return current
        current = current.parent

    # Case 3: Subdirectory containing spec/
    if (spec_dir / "spec" / "spec.yml").exists():
        return spec_dir / "spec"

    # Case 4: Try repo root
    repo_root = find_repo_root(start_path)
    if repo_root and (repo_root / "spec" / "spec.yml").exists():
        return repo_root / "spec"

    return None


# =============================================================================
# CLI Commands
# =============================================================================


def cmd_generate(spec_dir: Path, versions: list[str] | None, dry_run: bool, verbose: bool) -> int:
    """Generate inherited files AND sync tags for nested structure"""
    config = load_spec_config(spec_dir / "spec.yml")
    resolved_cache: dict[str, VersionSpec] = {}

    # Determine which versions to process
    target_versions = versions or [v for v in config if not v.startswith("_")]

    if not verbose:
        print(f"{'[DRY RUN] ' if dry_run else ''}Generating inherited specs + syncing tags...")
        print(f"Versions: {', '.join(target_versions)}")
        print()

    total_generated = 0
    total_removed = 0
    total_tags_synced = 0

    for version_name in target_versions:
        try:
            version = resolve_version(version_name, config)
            resolved_cache[version_name] = version

            # Generate inherited files
            result = generate_version(version, spec_dir, resolved_cache, dry_run=dry_run)

            # Sync tags for ALL files (including inherited ones just generated)
            tag_result = sync_version_tags(
                version, spec_dir, config, resolved_cache, dry_run=dry_run
            )

            prefix = "[DRY RUN] " if dry_run else ""

            has_changes = result.generated or result.removed or tag_result.generated

            if has_changes or verbose:
                inherits_str = f" (inherits {version.inherits_from})" if version.inherits_from else ""
                print(f"{version_name}{inherits_str}:")

                if verbose:
                    print(f"  Description: {version.description}")
                    print(f"  Tags: {', '.join(version.tags) if version.tags else 'none'}")

                for f in result.generated:
                    print(f"  {prefix}+ {f}")
                    total_generated += 1
                for f in result.removed:
                    print(f"  {prefix}- {f}")
                    total_removed += 1
                for f in tag_result.generated:
                    print(f"  {prefix}~ {f}")
                    total_tags_synced += 1

                if not has_changes:
                    # Count files for verbose mode
                    version_dir = spec_dir / version_name
                    new_count = len(scan_new_files(version_dir))
                    inherited_count = len(scan_inherited_files(version_dir))
                    print(f"  ({new_count} new, {inherited_count} inherited)")
            else:
                # Count files
                version_dir = spec_dir / version_name
                new_count = len(scan_new_files(version_dir))
                inherited_count = len(scan_inherited_files(version_dir))
                inherits_str = (
                    f" (inherits {version.inherits_from})" if version.inherits_from else ""
                )
                print(
                    f"{version_name}{inherits_str}: ({new_count} new, {inherited_count} inherited)"
                )

            for warning in result.warnings:
                print(f"  ! {warning}")
            for warning in tag_result.warnings:
                print(f"  ! {warning}")
            for error in tag_result.errors:
                print(f"  ERROR: {error}")

        except UcspecError as e:
            print(f"Error in {version_name}: {e}")
            return 1

    print()
    print(
        f"{'[DRY RUN] ' if dry_run else ''}Done: "
        f"{total_generated} generated, {total_removed} removed, {total_tags_synced} tags updated"
    )

    return 0


def cmd_clean(spec_dir: Path, versions: list[str] | None, dry_run: bool) -> int:
    """Remove all inherited files"""
    config = load_spec_config(spec_dir / "spec.yml")

    # Determine which versions to process
    target_versions = versions or [v for v in config if not v.startswith("_")]

    print(f"{'[DRY RUN] ' if dry_run else ''}Cleaning inherited specs...")
    print()

    total_removed = 0

    for version_name in target_versions:
        version_dir = spec_dir / version_name
        if not version_dir.exists():
            continue

        result = clean_version(version_dir, dry_run=dry_run)

        if result.removed:
            print(f"{version_name}:")
            for f in result.removed:
                print(f"  {'[DRY RUN] ' if dry_run else ''}- {f}")
                total_removed += 1

    print()
    print(f"{'[DRY RUN] ' if dry_run else ''}Removed: {total_removed} inherited files")

    return 0


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        prog="ucspec",
        description="Generate inherited test files for E2E spec suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ucspec                    Generate inherited files + sync tags (all versions)
  ucspec v302               Generate for specific version only
  ucspec v302 v303          Generate for multiple versions
  ucspec --dry-run          Preview changes without modifying files
  ucspec -n -v              Dry-run with verbose output
  ucspec clean              Remove all inherited files
  ucspec clean v302         Clean specific version only

File naming:
  - New specs: path/to/file.http (git-tracked)
  - Inherited: path/to/~file.http (generated from parent)

Tags are computed from spec.yml:
  - Version-level: tags: [r03, v301]
  - Pattern-level: tag_rules with glob patterns

Pattern syntax (fnmatch-style):
  "auth/**"           -> all files under auth/
  "**/authn.http"     -> all authn.http files anywhere
  "**/vuln-*.http"    -> filename pattern matching
""",
    )

    parser.add_argument(
        "-n", "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Only show errors",
    )
    parser.add_argument(
        "--spec-dir",
        type=Path,
        help="Path to spec directory (default: auto-detect)",
    )
    parser.add_argument(
        "args",
        nargs="*",
        metavar="[clean] [versions...]",
        help="Optional 'clean' command followed by version names",
    )

    args = parser.parse_args()

    # Parse positional args: first arg might be 'clean', rest are versions
    command = None
    versions = []
    for arg in args.args:
        if arg == "clean" and command is None:
            command = "clean"
        else:
            versions.append(arg)

    # Find spec directory
    spec_dir = find_spec_dir(args.spec_dir) if args.spec_dir else find_spec_dir()

    if not spec_dir:
        print("Error: Could not find spec.yml")
        print(f"Searched from: {Path.cwd()}")
        repo_root = find_repo_root()
        if repo_root:
            print(f"Found repo root: {repo_root}")
            print(f"Expected spec.yml at: {repo_root / 'spec' / 'spec.yml'}")
        return 1

    try:
        if command == "clean":
            return cmd_clean(spec_dir, versions or None, args.dry_run)
        else:
            # Default: generate
            return cmd_generate(
                spec_dir,
                versions or None,
                args.dry_run,
                args.verbose
            )
    except UcspecError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
