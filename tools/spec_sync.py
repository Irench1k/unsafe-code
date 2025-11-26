#!/usr/bin/env python3
"""
Spec Sync - Lean E2E test suite synchronization

Reads spec.yml and generates inherited test files locally.
Only new specs are stored in git; inherited files are generated on-demand.

Design principles:
- Lean: Only diffs stored in git (new specs + spec.yml)
- Implicit inheritance: Versions inherit all specs from parent
- Filename-based: No @specname tags needed, filename IS the spec name
- Flat structure: ~ prefix for inherited files (httpyac-friendly)
- Idempotent: Running multiple times is safe

File naming:
- New specs: {name}.http (stored in git)
- Inherited: ~{name}.http (generated, gitignored)

Commands:
- generate: Create ~inherited.http files
- clean: Remove all ~inherited.http files
- status: Show what would be generated (dry-run)
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Inherited file prefix - files starting with this are generated, not stored in git
INHERITED_PREFIX = "~"


@dataclass
class VersionSpec:
    """Resolved specification for a version"""

    name: str
    description: str
    tags: list[str]
    inherits_from: str | None
    specs: dict[str, Path]  # spec_name -> source_path (where content comes from)
    new_specs: set[str]  # specs defined in this version (not inherited)
    excluded_specs: set[str]  # specs explicitly excluded from parent


@dataclass
class SyncResult:
    """Result of a sync operation"""

    generated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    retagged: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class HttpRegionMeta:
    """Minimal HTTP region info for tagging"""

    start: int
    end: int
    name: str | None = None
    refs: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    tag_lines: list[int] = field(default_factory=list)
    has_request: bool = False


META_RE = re.compile(r"^\s*(#|//)\s*@(?P<key>[^\s]+)\s*(?P<val>.*)$")
REQUEST_LINE_RE = re.compile(r"^\s*(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|TRACE)\s+\S+", re.IGNORECASE)


def split_regions(lines: list[str]) -> list[tuple[int, int]]:
    """Split file into httpyac regions (keep delimiter with next region)."""
    regions: list[tuple[int, int]] = []
    start = 0
    for idx, line in enumerate(lines):
        if idx > start and line.lstrip().startswith("###"):
            regions.append((start, idx))
            start = idx
    regions.append((start, len(lines)))
    return regions


def parse_http_regions(lines: list[str]) -> list[HttpRegionMeta]:
    """Parse regions to capture names, refs, and tag lines."""
    regions: list[HttpRegionMeta] = []
    for start, end in split_regions(lines):
        region = HttpRegionMeta(start=start, end=end)
        for offset, line in enumerate(lines[start:end]):
            abs_idx = start + offset
            if REQUEST_LINE_RE.match(line):
                region.has_request = True
            meta = META_RE.match(line)
            if not meta:
                continue
            key = meta.group("key")
            val = meta.group("val").strip()
            if key == "name" and val:
                region.name = val
            elif key in ("ref", "forceRef") and val:
                for ref in [v.strip() for v in val.split(",") if v.strip()]:
                    region.refs.append(ref)
            elif key == "tag" and val:
                region.tags.extend([v.strip() for v in val.split(",") if v.strip()])
                region.tag_lines.append(abs_idx)
        regions.append(region)
    return regions


def retag_file_with_leaf_tags(path: Path, auto_tags: set[str]) -> bool:
    """Apply auto tags to leaf regions and remove them from non-leaf regions."""
    original = path.read_text()
    lines = original.splitlines()
    trailing_newline = "\n" if original.endswith("\n") else ""

    regions = parse_http_regions(lines)
    incoming: dict[str, int] = {r.name: 0 for r in regions if r.name}
    for region in regions:
        for ref in region.refs:
            if ref in incoming:
                incoming[ref] += 1

    new_lines: list[str] = []
    for region in regions:
        segment = lines[region.start : region.end]
        existing_tags = set(region.tags)
        manual_tags = {t for t in existing_tags if t not in auto_tags}
        is_leaf = region.has_request and not (region.name and incoming.get(region.name, 0) > 0)

        desired_tags = set(manual_tags)
        if is_leaf:
            desired_tags |= auto_tags

        remove_offsets = {line_idx - region.start for line_idx in region.tag_lines}
        segment_without_tags = [line for idx, line in enumerate(segment) if idx not in remove_offsets]

        if desired_tags:
            tag_line = f"# @tag {', '.join(sorted(desired_tags))}"
            request_idx = next((i for i, line in enumerate(segment_without_tags) if REQUEST_LINE_RE.match(line)), None)
            meta_idxs = [i for i, line in enumerate(segment_without_tags) if META_RE.match(line)]
            if meta_idxs:
                insert_at = meta_idxs[-1] + 1
            elif request_idx is not None:
                insert_at = request_idx
            else:
                insert_at = len(segment_without_tags)
            segment_without_tags.insert(insert_at, tag_line)

        new_lines.extend(segment_without_tags)

    updated = "\n".join(new_lines) + trailing_newline
    if updated != original:
        path.write_text(updated)
        return True
    return False


def retag_leaf_nodes(version: VersionSpec, spec_dir: Path, default_tags: set[str]) -> list[str]:
    """Ensure leaf requests carry default/version tags while non-leaves drop them."""
    version_dir = spec_dir / version.name
    if not version_dir.exists():
        return []

    auto_tags = set(default_tags) | set(version.tags)
    retagged: list[str] = []

    for path in sorted(version_dir.glob("*.http")):
        if path.is_file() and retag_file_with_leaf_tags(path, auto_tags):
            retagged.append(str(path.relative_to(spec_dir)))

    return retagged


class SpecSyncError(Exception):
    """Base exception for spec sync errors"""

    pass


def load_spec_config(spec_yml_path: Path) -> dict:
    """Load and validate spec.yml"""
    with open(spec_yml_path) as f:
        config = yaml.safe_load(f)

    if not config:
        raise SpecSyncError("spec.yml is empty")

    return config


def find_new_spec_file(version_dir: Path, spec_name: str) -> Path | None:
    """Find a new (non-inherited) spec file by name"""
    # Direct match: {name}.http
    direct = version_dir / f"{spec_name}.http"
    if direct.exists():
        return direct

    # Legacy format: spec.NN.new.{name}.http (for migration)
    for f in version_dir.glob(f"spec.*.new.{spec_name}.http"):
        return f

    return None


def get_inherited_path(version_dir: Path, spec_name: str) -> Path:
    """Get the path for an inherited spec file"""
    return version_dir / f"{INHERITED_PREFIX}{spec_name}.http"


def scan_existing_inherited(version_dir: Path) -> set[str]:
    """Find all existing inherited files in a version directory"""
    inherited = set()
    for f in version_dir.glob(f"{INHERITED_PREFIX}*.http"):
        # Extract spec name from ~{name}.http
        spec_name = f.stem[len(INHERITED_PREFIX) :]
        inherited.add(spec_name)
    return inherited


def scan_new_specs(version_dir: Path) -> dict[str, Path]:
    """Find all new (non-inherited) spec files in a version directory"""
    specs = {}

    for f in version_dir.glob("*.http"):
        name = f.name

        # Skip inherited files
        if name.startswith(INHERITED_PREFIX):
            continue

        # Skip .env and other non-spec files
        if not name.endswith(".http"):
            continue

        # Handle legacy format: spec.NN.new.{name}.http
        if name.startswith("spec.") and ".new." in name:
            # Extract: spec.01.new.foo-bar.http -> foo-bar
            parts = name.split(".")
            if len(parts) >= 4 and parts[2] == "new":
                spec_name = ".".join(parts[3:-1])  # Everything between 'new.' and '.http'
                specs[spec_name] = f
                continue

        # New format: {name}.http
        spec_name = f.stem
        specs[spec_name] = f

    return specs


def resolve_version(
    version_name: str, config: dict, spec_dir: Path, resolved_cache: dict[str, VersionSpec]
) -> VersionSpec:
    """
    Resolve a version's full spec list, including inherited specs.

    Uses caching to avoid re-resolving parent versions.
    """
    if version_name in resolved_cache:
        return resolved_cache[version_name]

    if version_name not in config:
        raise SpecSyncError(f"Version '{version_name}' not found in spec.yml")

    version_config = config[version_name]
    version_dir = spec_dir / version_name

    # Parse version config
    description = version_config.get("description", "")
    tags = version_config.get("tags", [])
    inherits_from = version_config.get("inherits")
    specs_list = version_config.get("specs", [])

    # Start with inherited specs if this version inherits
    final_specs: dict[str, Path] = {}
    if inherits_from:
        parent = resolve_version(inherits_from, config, spec_dir, resolved_cache)
        final_specs = dict(parent.specs)

    # Process exclusions first (specs NOT to inherit from parent)
    exclude_list = version_config.get("exclude", [])
    excluded_specs: set[str] = set()

    for spec_name in exclude_list:
        if spec_name in final_specs:
            del final_specs[spec_name]
            excluded_specs.add(spec_name)
        # Silently ignore excluding non-existent specs (might be removed upstream)

    # Process this version's new specs
    new_specs: set[str] = set()

    for spec_item in specs_list:
        if isinstance(spec_item, dict):
            # Legacy formats for backwards compatibility
            if "remove" in spec_item:
                # Legacy: {remove: spec-name} - now use 'exclude' list
                spec_name = spec_item["remove"]
                if spec_name in final_specs:
                    del final_specs[spec_name]
                    excluded_specs.add(spec_name)
            elif "inherits" in spec_item:
                # Legacy format: inherits: v301.spec-name
                inherit_ref = spec_item["inherits"]
                if "." not in inherit_ref:
                    raise SpecSyncError(f"Invalid inherit reference: {inherit_ref}")
                source_version, spec_name = inherit_ref.split(".", 1)
                source = resolve_version(source_version, config, spec_dir, resolved_cache)
                if spec_name not in source.specs:
                    raise SpecSyncError(
                        f"Spec '{spec_name}' not found in {source_version} "
                        f"(referenced by {version_name})"
                    )
                final_specs[spec_name] = source.specs[spec_name]
            elif "name" in spec_item:
                # Legacy format: name: spec-name (treated as new)
                spec_name = spec_item["name"]
                spec_file = find_new_spec_file(version_dir, spec_name)
                if spec_file:
                    final_specs[spec_name] = spec_file
                    new_specs.add(spec_name)
                else:
                    raise SpecSyncError(
                        f"New spec '{spec_name}' not found in {version_name}. "
                        f"Expected file: {version_dir}/{spec_name}.http"
                    )
        else:
            # Simple string: new spec name
            spec_name = spec_item
            spec_file = find_new_spec_file(version_dir, spec_name)
            if spec_file:
                final_specs[spec_name] = spec_file
                new_specs.add(spec_name)
            else:
                raise SpecSyncError(
                    f"New spec '{spec_name}' not found in {version_name}. "
                    f"Expected file: {version_dir}/{spec_name}.http"
                )

    result = VersionSpec(
        name=version_name,
        description=description,
        tags=tags,
        inherits_from=inherits_from,
        specs=final_specs,
        new_specs=new_specs,
        excluded_specs=excluded_specs,
    )

    resolved_cache[version_name] = result
    return result


def generate_version(
    version: VersionSpec, spec_dir: Path, dry_run: bool = False
) -> SyncResult:
    """Generate inherited files for a version"""
    result = SyncResult()
    version_dir = spec_dir / version.name

    # Ensure version directory exists
    if not version_dir.exists():
        if dry_run:
            result.warnings.append(f"Would create directory: {version_dir}")
        else:
            version_dir.mkdir(parents=True)

    # Create/update .env file
    env_file = version_dir / ".env"
    env_content = f"VERSION={version.name}\n"
    if not env_file.exists() or env_file.read_text() != env_content:
        if dry_run:
            result.generated.append(f"{version.name}/.env")
        else:
            env_file.write_text(env_content)
            result.generated.append(f"{version.name}/.env")

    # Find existing inherited files
    existing_inherited = scan_existing_inherited(version_dir)

    # Determine which specs need inherited files
    # (specs that come from other versions, not defined locally)
    new_spec_files = scan_new_specs(version_dir)

    for spec_name, source_path in version.specs.items():
        # Skip if this is a new spec in this version (has local file)
        if spec_name in new_spec_files:
            continue

        # This spec needs an inherited file
        inherited_path = get_inherited_path(version_dir, spec_name)
        source_content = source_path.read_text()

        needs_write = True
        if inherited_path.exists():
            if inherited_path.read_text() == source_content:
                needs_write = False
            existing_inherited.discard(spec_name)
        else:
            existing_inherited.discard(spec_name)

        if needs_write:
            if dry_run:
                result.generated.append(f"{version.name}/{INHERITED_PREFIX}{spec_name}.http")
            else:
                inherited_path.write_text(source_content)
                result.generated.append(f"{version.name}/{INHERITED_PREFIX}{spec_name}.http")

    # Remove orphaned inherited files
    for orphan_name in existing_inherited:
        orphan_path = get_inherited_path(version_dir, orphan_name)
        if dry_run:
            result.removed.append(f"{version.name}/{INHERITED_PREFIX}{orphan_name}.http")
        else:
            orphan_path.unlink()
            result.removed.append(f"{version.name}/{INHERITED_PREFIX}{orphan_name}.http")

    return result


def clean_version(version_dir: Path, dry_run: bool = False) -> SyncResult:
    """Remove all inherited files from a version directory (both new and legacy formats)"""
    result = SyncResult()

    # New format: ~{name}.http
    for f in version_dir.glob(f"{INHERITED_PREFIX}*.http"):
        if dry_run:
            result.removed.append(str(f.relative_to(version_dir.parent)))
        else:
            f.unlink()
            result.removed.append(str(f.relative_to(version_dir.parent)))

    # Legacy format: spec.NN.inherited.{name}.http
    for f in version_dir.glob("spec.*.inherited.*.http"):
        if dry_run:
            result.removed.append(str(f.relative_to(version_dir.parent)))
        else:
            f.unlink()
            result.removed.append(str(f.relative_to(version_dir.parent)))

    return result


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


def cmd_migrate(spec_dir: Path, versions: list[str] | None, dry_run: bool) -> int:
    """Migrate from legacy spec.NN.new.{name}.http to {name}.http format"""
    config = load_spec_config(spec_dir / "spec.yml")

    # Determine which versions to process
    if versions:
        target_versions = versions
    else:
        target_versions = [v for v in config.keys() if not v.startswith("_")]

    print(f"{'[DRY RUN] ' if dry_run else ''}Migrating to new file format...")
    print(f"Spec directory: {spec_dir}")
    print()

    total_renamed = 0
    total_removed = 0

    for version_name in target_versions:
        version_dir = spec_dir / version_name
        if not version_dir.exists():
            continue

        renamed = []
        removed = []

        # Rename spec.NN.new.{name}.http -> {name}.http
        for f in sorted(version_dir.glob("spec.*.new.*.http")):
            parts = f.name.split(".")
            if len(parts) >= 4 and parts[2] == "new":
                spec_name = ".".join(parts[3:-1])
                new_path = version_dir / f"{spec_name}.http"

                if new_path.exists() and new_path != f:
                    # Target exists - skip (might be duplicate)
                    continue

                if dry_run:
                    renamed.append(f"{f.name} -> {new_path.name}")
                else:
                    f.rename(new_path)
                    renamed.append(f"{f.name} -> {new_path.name}")

        # Remove legacy inherited files (spec.NN.inherited.*.http)
        for f in sorted(version_dir.glob("spec.*.inherited.*.http")):
            if dry_run:
                removed.append(f.name)
            else:
                f.unlink()
                removed.append(f.name)

        if renamed or removed:
            print(f"{version_name}:")
            prefix = "[DRY RUN] " if dry_run else ""
            for r in renamed:
                print(f"  {prefix}→ {r}")
                total_renamed += 1
            for r in removed:
                print(f"  {prefix}- {r}")
                total_removed += 1

    print()
    print(f"{'[DRY RUN] ' if dry_run else ''}Summary: {total_renamed} renamed, {total_removed} removed")

    return 0


def cmd_generate(spec_dir: Path, versions: list[str] | None, dry_run: bool) -> int:
    """Generate inherited files"""
    config = load_spec_config(spec_dir / "spec.yml")
    resolved_cache: dict[str, VersionSpec] = {}

    # Determine which versions to process
    if versions:
        target_versions = versions
    else:
        target_versions = [v for v in config.keys() if not v.startswith("_")]

    print(f"{'[DRY RUN] ' if dry_run else ''}Generating inherited specs...")
    print(f"Spec directory: {spec_dir}")
    print(f"Versions: {', '.join(target_versions)}")
    print()

    total_generated = 0
    total_removed = 0
    total_retagged = 0

    for version_name in target_versions:
        try:
            version = resolve_version(version_name, config, spec_dir, resolved_cache)
            result = generate_version(version, spec_dir, dry_run=dry_run)
            if not dry_run:
                result.retagged.extend(retag_leaf_nodes(version, spec_dir, {"ci"}))

            # Print results
            prefix = "[DRY RUN] " if dry_run else ""

            if result.generated or result.removed or result.retagged:
                print(f"{version_name}:")
                for f in result.generated:
                    print(f"  {prefix}+ {f}")
                    total_generated += 1
                for f in result.removed:
                    print(f"  {prefix}- {f}")
                    total_removed += 1
                for f in result.retagged:
                    print(f"  {prefix}~ {f}")
                    total_retagged += 1
            else:
                inherited_count = len(version.specs) - len(version.new_specs)
                print(f"{version_name}: ✓ ({len(version.new_specs)} new, {inherited_count} inherited)")

            for warning in result.warnings:
                print(f"  ⚠ {warning}")

        except SpecSyncError as e:
            print(f"Error in {version_name}: {e}")
            return 1

    print()
    print(
        f"{'[DRY RUN] ' if dry_run else ''}Summary: {total_generated} generated, "
        f"{total_removed} removed, {total_retagged} retagged"
    )

    return 0


def cmd_clean(spec_dir: Path, versions: list[str] | None, dry_run: bool) -> int:
    """Remove all inherited files"""
    config = load_spec_config(spec_dir / "spec.yml")

    # Determine which versions to process
    if versions:
        target_versions = versions
    else:
        target_versions = [v for v in config.keys() if not v.startswith("_")]

    print(f"{'[DRY RUN] ' if dry_run else ''}Cleaning inherited specs...")
    print(f"Spec directory: {spec_dir}")
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


def cmd_status(spec_dir: Path, versions: list[str] | None) -> int:
    """Show status of all versions"""
    config = load_spec_config(spec_dir / "spec.yml")
    resolved_cache: dict[str, VersionSpec] = {}

    # Determine which versions to show
    if versions:
        target_versions = versions
    else:
        target_versions = [v for v in config.keys() if not v.startswith("_")]

    print(f"Spec Suite Status")
    print(f"Directory: {spec_dir}")
    print()

    for version_name in target_versions:
        try:
            version = resolve_version(version_name, config, spec_dir, resolved_cache)
            version_dir = spec_dir / version_name

            # Count files
            existing_inherited = scan_existing_inherited(version_dir) if version_dir.exists() else set()
            new_spec_files = scan_new_specs(version_dir) if version_dir.exists() else {}

            # Expected inherited
            expected_inherited = set(version.specs.keys()) - set(new_spec_files.keys())

            # Status
            missing = expected_inherited - existing_inherited
            orphaned = existing_inherited - expected_inherited

            status = "✓" if not missing and not orphaned else "!"

            inherits_str = f" (inherits {version.inherits_from})" if version.inherits_from else ""
            print(f"{status} {version_name}{inherits_str}")
            print(f"    {version.description}")
            print(f"    New: {len(version.new_specs)}, Inherited: {len(expected_inherited)}")

            if missing:
                print(f"    Missing inherited: {', '.join(sorted(missing))}")
            if orphaned:
                print(f"    Orphaned inherited: {', '.join(sorted(orphaned))}")

            print()

        except SpecSyncError as e:
            print(f"! {version_name}: Error - {e}")
            print()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Sync E2E test suite - generate inherited files from spec.yml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  generate    Create ~inherited.http files for all/specified versions
  clean       Remove all ~inherited.http files (both new and legacy formats)
  status      Show current state without making changes
  migrate     Convert legacy spec.NN.new.*.http to {name}.http format

Examples:
  uv run spec-sync generate              # Generate all inherited files
  uv run spec-sync generate v302 v303    # Generate for specific versions
  uv run spec-sync generate --dry-run    # Preview what would be generated
  uv run spec-sync clean                 # Remove all inherited files
  uv run spec-sync status                # Show what's missing/orphaned
  uv run spec-sync migrate --dry-run     # Preview migration from legacy format

File naming:
  - New specs: {name}.http (stored in git)
  - Inherited: ~{name}.http (generated, gitignored)

spec.yml format:
  inherits: vXXX        # inherit all specs from parent version
  exclude: [...]        # don't inherit these specs from parent
  specs: [...]          # new specs defined in this version

The tool:
  1. Reads spec.yml for version inheritance rules
  2. Resolves full spec list for each version
  3. Generates inherited files by copying from source versions
  4. Removes orphaned inherited files
        """,
    )

    parser.add_argument(
        "command",
        choices=["generate", "clean", "status", "migrate"],
        help="Command to execute",
    )
    parser.add_argument(
        "versions",
        nargs="*",
        help="Specific versions to process (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--spec-dir",
        type=Path,
        help="Path to spec directory (default: auto-detect)",
    )

    args = parser.parse_args()

    # Find spec directory
    if args.spec_dir:
        spec_dir = find_spec_dir(args.spec_dir)
    else:
        spec_dir = find_spec_dir()

    if not spec_dir:
        print("Error: Could not find spec.yml")
        print(f"Searched from: {Path.cwd()}")
        repo_root = find_repo_root()
        if repo_root:
            print(f"Found repo root: {repo_root}")
            print(f"Expected spec.yml at: {repo_root / 'spec' / 'spec.yml'}")
        return 1

    try:
        if args.command == "generate":
            return cmd_generate(spec_dir, args.versions or None, args.dry_run)
        elif args.command == "clean":
            return cmd_clean(spec_dir, args.versions or None, args.dry_run)
        elif args.command == "status":
            return cmd_status(spec_dir, args.versions or None)
        elif args.command == "migrate":
            return cmd_migrate(spec_dir, args.versions or None, args.dry_run)
    except SpecSyncError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
