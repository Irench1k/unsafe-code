#!/usr/bin/env python3
"""
Spec Sync - Intelligent E2E test suite synchronization

Reads spec.yml and synchronizes test files based on inheritance rules.
Handles file copying, renaming, reordering, and cleanup.

Design principles:
- Idempotent: Running multiple times is safe
- Safe: Only removes .inherited. files, never .new. files
- Smart: Matches files by @specname, not filename
- Clean: Removes orphaned files, maintains numbering
"""

import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SpecFile:
    """Represents a spec file with metadata"""

    path: Path
    specname: str
    is_new: bool
    is_inherited: bool
    number: int | None

    @property
    def version(self) -> str:
        return self.path.parent.name

    def __repr__(self):
        return f"SpecFile({self.path.name}, specname={self.specname})"


class SpecSyncError(Exception):
    """Base exception for spec sync errors"""

    pass


def extract_specname(file_path: Path) -> str | None:
    """Extract @specname from file header"""
    try:
        with open(file_path) as f:
            for line_num, line in enumerate(f, 1):
                if line_num > 20:  # Only check first 20 lines
                    break
                match = re.match(r"^\s*#\s*@specname\s*=\s*(.+)\s*$", line)
                if match:
                    return match.group(1).strip()
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")
    return None


def scan_version_directory(version_dir: Path) -> list[SpecFile]:
    """Scan a version directory and extract all spec files"""
    specs = []

    for file_path in sorted(version_dir.glob("*.http")):
        # Parse filename pattern: spec.NN.TYPE.NAME.http
        name = file_path.stem
        match = re.match(r"^spec\.(\d+)\.(new|inherited)\.(.+)$", name)

        if not match:
            # Unknown file pattern - we'll report this later
            continue

        number = int(match.group(1))
        file_type = match.group(2)
        # name_part = match.group(3)  # Extracted but not currently used

        specname = extract_specname(file_path)
        if not specname:
            print(f"Warning: {file_path.name} has no @specname marker")
            continue

        specs.append(
            SpecFile(
                path=file_path,
                specname=specname,
                is_new=(file_type == "new"),
                is_inherited=(file_type == "inherited"),
                number=number,
            )
        )

    return specs


def find_spec_by_name(specs: list[SpecFile], specname: str) -> SpecFile | None:
    """Find a spec file by its @specname"""
    matches = [s for s in specs if s.specname == specname]
    if len(matches) == 0:
        return None
    if len(matches) > 1:
        raise SpecSyncError(
            f"Multiple files found with @specname='{specname}': {[s.path.name for s in matches]}"
        )
    return matches[0]


def load_spec_config(spec_yml_path: Path) -> dict:
    """Load and validate spec.yml"""
    with open(spec_yml_path) as f:
        config = yaml.safe_load(f)

    if not config:
        raise SpecSyncError("spec.yml is empty")

    return config


def generate_filename(number: int, spec_type: str, specname: str) -> str:
    """Generate standardized filename"""
    return f"spec.{number:02d}.{spec_type}.{specname}.http"


def sync_version(
    version_name: str, version_config: dict, spec_dir: Path, dry_run: bool = False
) -> None:
    """Sync a single version directory"""
    version_dir = spec_dir / version_name
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Syncing {version_name}...")

    # Create directory if needed
    if not version_dir.exists():
        print(f"  Creating directory: {version_dir}")
        if not dry_run:
            version_dir.mkdir(parents=True)

    # Create/update .env file
    env_file = version_dir / ".env"
    env_content = f"VERSION={version_name}\n"
    if not env_file.exists() or env_file.read_text() != env_content:
        print(f"  {'Would write' if dry_run else 'Writing'} {env_file.name}")
        if not dry_run:
            env_file.write_text(env_content)

    # Scan existing files
    existing_specs = scan_version_directory(version_dir)

    # Check for unknown files (not matching our pattern)
    all_files = {f.name for f in version_dir.glob("*.http")}
    known_files = {s.path.name for s in existing_specs}
    unknown_files = all_files - known_files

    if unknown_files:
        print(f"  WARNING: Unknown files in {version_name}: {sorted(unknown_files)}")
        print("  These files don't match the spec.NN.(new|inherited).NAME.http pattern")
        print("  Please add @specname markers or rename them appropriately")

    # Build expected spec list
    expected_specs = []
    specs_config = version_config.get("specs", [])

    for spec_item in specs_config:
        if isinstance(spec_item, dict) and "inherits" in spec_item:
            # Inherited spec: "v100.menu" -> find in v100
            inherit_ref = spec_item["inherits"]
            if "." not in inherit_ref:
                raise SpecSyncError(
                    f"Invalid inherit reference: {inherit_ref} (expected 'vXXX.name')"
                )

            source_version, specname = inherit_ref.split(".", 1)
            expected_specs.append(
                {"type": "inherited", "specname": specname, "source_version": source_version}
            )
        elif isinstance(spec_item, dict) and "name" in spec_item:
            # New spec
            expected_specs.append({"type": "new", "specname": spec_item["name"]})
        else:
            raise SpecSyncError(f"Invalid spec item in {version_name}: {spec_item}")

    # Process each expected spec
    for i, expected in enumerate(expected_specs, 1):
        specname = expected["specname"]
        spec_type = expected["type"]
        target_filename = generate_filename(i, spec_type, specname)
        target_path = version_dir / target_filename

        if spec_type == "inherited":
            # Copy from source version
            source_version = expected["source_version"]
            source_dir = spec_dir / source_version

            if not source_dir.exists():
                raise SpecSyncError(f"Source version {source_version} does not exist")

            source_specs = scan_version_directory(source_dir)
            source_spec = find_spec_by_name(source_specs, specname)

            if not source_spec:
                raise SpecSyncError(
                    f"Spec '{specname}' not found in {source_version} "
                    f"(referenced by {version_name})"
                )

            # Check if target exists and is up-to-date
            needs_copy = True
            if target_path.exists():
                # Compare content (ignoring @specname line for comparison)
                source_content = source_spec.path.read_text()
                target_content = target_path.read_text()
                if source_content == target_content:
                    needs_copy = False

            if needs_copy:
                print(
                    f"  {'Would copy' if dry_run else 'Copying'} {specname} from {source_version} -> {target_filename}"
                )
                if not dry_run:
                    shutil.copy2(source_spec.path, target_path)
            else:
                print(f"  ✓ {target_filename} (up-to-date)")

        else:  # new
            # Find existing .new. file with matching @specname
            existing_new = find_spec_by_name([s for s in existing_specs if s.is_new], specname)

            if not existing_new:
                raise SpecSyncError(
                    f"Expected new spec '{specname}' in {version_name} but not found. "
                    f"Please create a file with @specname = {specname}"
                )

            # Rename if needed
            if existing_new.path.name != target_filename:
                print(
                    f"  {'Would rename' if dry_run else 'Renaming'} {existing_new.path.name} -> {target_filename}"
                )
                if not dry_run:
                    existing_new.path.rename(target_path)
            else:
                print(f"  ✓ {target_filename} (correct)")

    # Clean up orphaned .inherited. files
    expected_inherited_names = {
        generate_filename(i + 1, "inherited", exp["specname"])
        for i, exp in enumerate(expected_specs)
        if exp["type"] == "inherited"
    }

    for spec in existing_specs:
        if spec.is_inherited and spec.path.name not in expected_inherited_names:
            print(f"  {'Would remove' if dry_run else 'Removing'} orphaned {spec.path.name}")
            if not dry_run:
                spec.path.unlink()

    print(f"  ✓ {version_name} sync complete")


def sync_all(spec_dir: Path, dry_run: bool = False) -> None:
    """Sync all versions based on spec.yml"""
    spec_yml = spec_dir / "spec.yml"

    if not spec_yml.exists():
        raise SpecSyncError(f"spec.yml not found in {spec_dir}")

    config = load_spec_config(spec_yml)

    print(f"{'=' * 70}")
    print(f"{'DRY RUN - ' if dry_run else ''}Syncing E2E Spec Suite")
    print(f"{'=' * 70}")
    print(f"Config: {spec_yml}")
    print(f"Versions: {', '.join(config.keys())}")

    for version_name, version_config in config.items():
        if version_name.startswith("_"):
            # Skip metadata entries
            continue

        sync_version(version_name, version_config, spec_dir, dry_run=dry_run)

    print(f"\n{'=' * 70}")
    print(f"{'[DRY RUN] ' if dry_run else ''}Sync complete!")
    print(f"{'=' * 70}")


def find_repo_root(start_path: Path = None) -> Path | None:
    """Find repo root by looking for pyproject.toml"""
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # Walk up until we find pyproject.toml or reach filesystem root
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent

    return None


def find_spec_dir(start_path: Path = None) -> Path:
    """
    Find the spec directory from anywhere in the repo.
    Handles:
    - Running from repo root
    - Running from spec/ directory
    - Running from spec/vXXX subdirectory
    - Passing explicit path as argument
    """
    if start_path is None:
        start_path = Path.cwd()

    spec_dir = start_path.resolve()

    # Case 1: Already in spec dir with spec.yml
    if (spec_dir / "spec.yml").exists():
        return spec_dir

    # Case 2: In a version subdirectory (spec/v100, etc.)
    # Walk up to find spec.yml
    current = spec_dir
    while current != current.parent:
        if (current / "spec.yml").exists():
            return current
        current = current.parent

    # Case 3: User passed a path that's a subdirectory containing spec/
    if (spec_dir / "spec" / "spec.yml").exists():
        return spec_dir / "spec"

    # Case 4: Try to find repo root and use spec/ from there
    repo_root = find_repo_root(start_path)
    if repo_root and (repo_root / "spec" / "spec.yml").exists():
        return repo_root / "spec"

    # Not found
    return None


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Sync E2E test suite based on spec.yml",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From anywhere in the repo
  uv run spec-sync
  uv run spec-sync --dry-run

  # Specify explicit directory
  uv run spec-sync /path/to/spec

The tool will:
  1. Auto-detect repo root and spec/ directory
  2. Read spec.yml to understand inheritance
  3. Create version directories with .env files
  4. Copy inherited tests from source versions
  5. Rename/reorder new tests to match sequence
  6. Remove orphaned .inherited. files
  7. Validate @specname markers

Safety features:
  - Only removes .inherited. files (never .new.)
  - Validates all references exist
  - Detects unknown files
  - Idempotent (safe to run multiple times)
        """,
    )

    parser.add_argument(
        "spec_dir", nargs="?", default=None, help="Path to spec directory (default: auto-detect)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without modifying files"
    )

    args = parser.parse_args()

    # Find spec directory
    if args.spec_dir:
        spec_dir = Path(args.spec_dir).resolve()
        if not spec_dir.exists():
            print(f"Error: Directory not found: {spec_dir}")
            sys.exit(1)

        # Try to find spec.yml in or under this directory
        spec_dir = find_spec_dir(spec_dir)
    else:
        # Auto-detect from current directory
        spec_dir = find_spec_dir()

    if not spec_dir:
        print("Error: Could not find spec.yml")
        print(f"Searched from: {Path.cwd()}")
        repo_root = find_repo_root()
        if repo_root:
            print(f"Found repo root: {repo_root}")
            print(f"Expected spec.yml at: {repo_root / 'spec' / 'spec.yml'}")
        else:
            print("Could not find repo root (looked for pyproject.toml)")
        sys.exit(1)

    try:
        sync_all(spec_dir, dry_run=args.dry_run)
    except SpecSyncError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
