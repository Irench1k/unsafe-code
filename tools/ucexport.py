#!/usr/bin/env python3
"""
ucexport - Export curated content from develop to main branch.

This tool synchronizes a student-friendly subset of the develop branch to main.
It uses git worktree for safe, isolated operations and provides human oversight
before any changes are pushed.

Usage:
    uv run ucexport              # Preview what would be exported (no side effects)
    uv run ucexport --apply      # Apply changes locally (still requires manual push)
    uv run ucexport --cleanup    # Remove any stale worktrees from previous runs

The tool will:
1. Clean up any existing worktrees from previous runs
2. Create a temporary git worktree for the main branch
3. Clear all existing content (except .git)
4. Copy the curated export from develop
5. Show a diff of changes
6. Commit (apply mode only) and clean up the worktree
7. Provide instructions for pushing or undoing

Safety features:
- Never pushes automatically - requires explicit user action
- Uses git worktree for isolation - develop branch is never modified
- ALWAYS cleans up worktrees after completion - no lingering state
- Validates all preconditions before any destructive operations
- Provides clear error messages and recovery instructions
"""

from __future__ import annotations

import argparse
import atexit
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import NoReturn


# =============================================================================
# Configuration: What gets exported to main
# =============================================================================

# Prefix used to identify our worktrees
WORKTREE_PREFIX = "ucexport-main-"


@dataclass(frozen=True)
class ExportConfig:
    """Defines what gets exported from develop to main."""

    # Source directories to copy (relative to repo root)
    # Format: (source_path, destination_path)
    directory_mappings: tuple[tuple[str, str], ...] = (
        ("vulnerabilities/python/flask/confusion", "flask-confusion"),
    )

    # Individual files to copy (relative to repo root)
    # Format: (source_path, destination_path)
    file_mappings: tuple[tuple[str, str], ...] = (
        ("LICENSE", "LICENSE"),
        ("SECURITY.md", "SECURITY.md"),
    )

    # Files that need transformation (will be generated, not copied)
    # These are handled specially in the export logic
    generated_files: tuple[str, ...] = (
        "README.md",
        "CONTRIBUTING.md",
    )

    # Branch names
    source_branch: str = "develop"
    target_branch: str = "main"


# =============================================================================
# Error handling
# =============================================================================

class ExportError(Exception):
    """Base exception for export errors."""
    pass


class PreconditionError(ExportError):
    """Raised when preconditions are not met."""
    pass


class GitError(ExportError):
    """Raised when a git operation fails."""
    pass


class ExitCode(Enum):
    """Exit codes for the tool."""
    SUCCESS = 0
    PRECONDITION_FAILED = 1
    GIT_ERROR = 2
    UNEXPECTED_ERROR = 3
    USER_ABORT = 4


def die(message: str, exit_code: ExitCode = ExitCode.UNEXPECTED_ERROR) -> NoReturn:
    """Print error message and exit."""
    print(f"\n❌ ERROR: {message}", file=sys.stderr)
    print(f"\nExit code: {exit_code.value} ({exit_code.name})", file=sys.stderr)
    sys.exit(exit_code.value)


def warn(message: str) -> None:
    """Print warning message."""
    print(f"⚠️  WARNING: {message}", file=sys.stderr)


def info(message: str) -> None:
    """Print info message."""
    print(f"ℹ️  {message}")


def success(message: str) -> None:
    """Print success message."""
    print(f"✅ {message}")


# =============================================================================
# Git utilities with paranoid error handling
# =============================================================================

@dataclass
class GitContext:
    """Context for git operations."""
    repo_root: Path
    worktree_path: Path | None = None
    config: ExportConfig = field(default_factory=ExportConfig)
    _cleanup_registered: bool = field(default=False, repr=False)

    def run_git(
        self,
        *args: str,
        cwd: Path | None = None,
        capture: bool = True,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a git command with proper error handling."""
        cmd = ["git", *args]
        cwd = cwd or self.repo_root

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=capture,
                text=True,
                check=False,  # We'll check manually for better error messages
            )

            if check and result.returncode != 0:
                stderr = result.stderr.strip() if result.stderr else "(no stderr)"
                raise GitError(
                    f"Git command failed: {' '.join(cmd)}\n"
                    f"Exit code: {result.returncode}\n"
                    f"Stderr: {stderr}"
                )

            return result

        except FileNotFoundError:
            raise GitError("git executable not found. Is git installed?")
        except Exception as e:
            if isinstance(e, GitError):
                raise
            raise GitError(f"Unexpected error running git: {e}")

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        result = self.run_git("rev-parse", "--abbrev-ref", "HEAD")
        return result.stdout.strip()

    def get_commit_sha(self, ref: str, cwd: Path | None = None) -> str:
        """Get the full SHA of a ref."""
        result = self.run_git("rev-parse", ref, cwd=cwd)
        return result.stdout.strip()

    def branch_exists(self, branch: str) -> bool:
        """Check if a branch exists."""
        result = self.run_git(
            "rev-parse", "--verify", f"refs/heads/{branch}",
            check=False
        )
        return result.returncode == 0

    def is_working_tree_clean(self) -> bool:
        """Check if the working tree is clean."""
        result = self.run_git("status", "--porcelain")
        return not result.stdout.strip()

    def list_worktrees(self) -> list[tuple[Path, str | None]]:
        """
        List all existing worktrees.
        Returns list of (path, branch) tuples.
        """
        result = self.run_git("worktree", "list", "--porcelain")
        worktrees: list[tuple[Path, str | None]] = []

        current_path: Path | None = None
        current_branch: str | None = None

        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                if current_path is not None:
                    worktrees.append((current_path, current_branch))
                current_path = Path(line[9:])
                current_branch = None
            elif line.startswith("branch "):
                current_branch = line[7:].replace("refs/heads/", "")

        if current_path is not None:
            worktrees.append((current_path, current_branch))

        return worktrees

    def find_ucexport_worktrees(self) -> list[tuple[Path, str | None]]:
        """Find all worktrees created by ucexport (by prefix or branch)."""
        worktrees = self.list_worktrees()
        ucexport_worktrees = []

        for path, branch in worktrees:
            # Skip the main repo
            if path == self.repo_root:
                continue

            # Match by directory name prefix OR by being on the target branch
            if (WORKTREE_PREFIX in path.name or
                branch == self.config.target_branch):
                ucexport_worktrees.append((path, branch))

        return ucexport_worktrees

    def cleanup_worktree(self, worktree_path: Path, silent: bool = False) -> bool:
        """
        Clean up a worktree safely.
        Returns True if cleanup was successful.
        """
        cleaned = False

        # First try git worktree remove
        try:
            result = self.run_git(
                "worktree", "remove", "--force", str(worktree_path),
                check=False
            )
            if result.returncode == 0:
                cleaned = True
                if not silent:
                    info(f"Removed worktree: {worktree_path}")
        except Exception:
            pass

        # Also try to remove the directory if it still exists
        try:
            if worktree_path.exists():
                shutil.rmtree(worktree_path)
                cleaned = True
                if not silent:
                    info(f"Removed directory: {worktree_path}")
        except Exception as e:
            if not silent:
                warn(f"Could not remove directory {worktree_path}: {e}")

        # Prune stale worktree entries
        try:
            self.run_git("worktree", "prune", check=False)
        except Exception:
            pass

        return cleaned

    def cleanup_all_ucexport_worktrees(self, silent: bool = False) -> int:
        """
        Clean up all worktrees created by ucexport.
        Returns count of worktrees cleaned.
        """
        worktrees = self.find_ucexport_worktrees()
        cleaned = 0

        for path, branch in worktrees:
            if self.cleanup_worktree(path, silent=silent):
                cleaned += 1

        return cleaned


# =============================================================================
# Precondition checks
# =============================================================================

def check_preconditions(ctx: GitContext, cleanup_existing: bool = True) -> None:
    """
    Validate all preconditions before proceeding.

    If cleanup_existing is True, automatically cleans up any existing
    ucexport worktrees before checking preconditions.
    """
    info("Checking preconditions...")

    # 1. Must be in a git repository
    if not (ctx.repo_root / ".git").exists():
        raise PreconditionError(
            f"Not a git repository: {ctx.repo_root}\n"
            "Run this command from the repository root."
        )

    # 2. Must be on the source branch (develop)
    current_branch = ctx.get_current_branch()
    if current_branch != ctx.config.source_branch:
        raise PreconditionError(
            f"Must be on '{ctx.config.source_branch}' branch, but currently on '{current_branch}'.\n"
            f"Run: git checkout {ctx.config.source_branch}"
        )

    # 3. Working tree should be clean (warning, not error)
    if not ctx.is_working_tree_clean():
        warn(
            "Working tree has uncommitted changes.\n"
            "   These changes will NOT be included in the export.\n"
            "   Consider committing or stashing them first."
        )

    # 4. Target branch must exist
    if not ctx.branch_exists(ctx.config.target_branch):
        raise PreconditionError(
            f"Target branch '{ctx.config.target_branch}' does not exist.\n"
            f"Create it first with: git branch {ctx.config.target_branch} origin/{ctx.config.target_branch}"
        )

    # 5. Source directories must exist
    for source_dir, _ in ctx.config.directory_mappings:
        source_path = ctx.repo_root / source_dir
        if not source_path.is_dir():
            raise PreconditionError(
                f"Source directory does not exist: {source_dir}\n"
                "Has the repository structure changed?"
            )

    # 6. Source files must exist
    for source_file, _ in ctx.config.file_mappings:
        source_path = ctx.repo_root / source_file
        if not source_path.is_file():
            raise PreconditionError(
                f"Source file does not exist: {source_file}\n"
                "Has the repository structure changed?"
            )

    # 7. Clean up any existing ucexport worktrees
    if cleanup_existing:
        existing = ctx.find_ucexport_worktrees()
        if existing:
            info(f"Found {len(existing)} existing ucexport worktree(s), cleaning up...")
            cleaned = ctx.cleanup_all_ucexport_worktrees()
            if cleaned > 0:
                success(f"Cleaned up {cleaned} stale worktree(s)")

    success("All preconditions met")


# =============================================================================
# Export content generation
# =============================================================================

def generate_main_readme(ctx: GitContext) -> str:
    """Generate the README.md for the main branch."""
    return '''# Unsafe Code Lab

> Learn to spot real-world vulnerabilities in production-quality code.

## Quick Start

```bash
git clone https://github.com/Irench1k/unsafe-code
cd unsafe-code/flask-confusion
docker compose up -d
```

Then open any `.http` file in VSCode with the [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension.

## What's Inside

**[Flask Confusion Vulnerabilities](flask-confusion/)** — A progressive curriculum exploring how different parts of an application can "disagree" about the same data:

| Section | Focus |
|---------|-------|
| [Input Source](flask-confusion/webapp/r01_input_source_confusion/) | Where does the data come from? |
| [Authentication](flask-confusion/webapp/r02_authentication_confusion/) | Who is making the request? |
| [Authorization](flask-confusion/webapp/r03_authorization_confusion/) | What are they allowed to do? |
| [Cardinality](flask-confusion/webapp/r04_cardinality_confusion/) | How many values? How many resources? |
| [Normalization](flask-confusion/webapp/r05_normalization_issues/) | Are these two strings "equal"? |

Each section contains multiple exercises with:
- Realistic vulnerable code (not CTF puzzles)
- Interactive `.http` demos showing the exploit
- Fixed versions demonstrating the secure pattern

## Target Audience

- **Developers** learning secure coding practices
- **AppSec engineers** preparing training materials
- **Students** with CTF/pentesting experience moving to code review

## Contributing

Development happens on the [`develop`](https://github.com/Irench1k/unsafe-code/tree/develop) branch. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the terms in [LICENSE](LICENSE).
'''


def generate_main_contributing(ctx: GitContext) -> str:
    """Generate the CONTRIBUTING.md for the main branch."""
    return '''# Contributing to Unsafe Code Lab

Thank you for your interest in contributing!

## Development Setup

Development happens on the `develop` branch, which contains additional tooling and infrastructure not needed by end users.

```bash
# Clone and switch to develop
git clone https://github.com/Irench1k/unsafe-code
cd unsafe-code
git checkout develop

# Install development dependencies
uv sync --all-extras

# Start the Flask app
cd vulnerabilities/python/flask/confusion
docker compose up -d
```

## Quick Start

1. Navigate to an exercise directory (e.g., `flask-confusion/webapp/r01_input_source_confusion/e01_dual_parameters/`)
2. Read the `README.md` to understand the vulnerability
3. Open the `.http` files in VSCode with REST Client
4. Study the source code to understand why the vulnerability exists

## What Makes a Good Vulnerability Example

We create **realistic vulnerabilities** that emerge from natural coding patterns:

- Refactoring drift (decorator reads different source than handler)
- Feature additions that introduce edge cases
- Framework helper functions with subtle precedence rules

**Avoid:**
- CTF-style puzzles or contrived code
- Obvious markers like `# VULNERABILITY HERE`
- Code that would fail a normal code review for non-security reasons

## Reporting Issues

Please open an issue on GitHub for:
- Bugs in the vulnerable code (that aren't the intended vulnerability!)
- Documentation improvements
- New vulnerability ideas

## Code of Conduct

Be respectful and constructive. This is an educational project.
'''


def copy_with_structure(src: Path, dst: Path, ctx: GitContext) -> int:
    """
    Copy a directory tree, preserving structure.
    Returns the number of files copied.
    """
    if not src.is_dir():
        raise ExportError(f"Source is not a directory: {src}")

    file_count = 0

    for item in src.rglob("*"):
        if item.is_file():
            # Skip Python cache and other artifacts
            if "__pycache__" in item.parts:
                continue
            if item.suffix == ".pyc":
                continue
            if item.name == ".DS_Store":
                continue

            rel_path = item.relative_to(src)
            dst_file = dst / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dst_file)
            file_count += 1

    return file_count


def clear_directory(path: Path, keep: tuple[str, ...] = (".git",)) -> int:
    """
    Remove all contents of a directory except specified items.
    Returns the number of items removed.
    """
    removed = 0
    for item in path.iterdir():
        if item.name in keep:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
        removed += 1
    return removed


# =============================================================================
# Main export logic
# =============================================================================

@dataclass
class ExportResult:
    """Result of an export operation."""
    worktree_path: Path
    files_copied: int
    files_removed: int
    commit_created: bool
    commit_sha: str | None
    old_main_sha: str
    diff_stat: str
    has_changes: bool


def perform_export(ctx: GitContext, apply: bool = False) -> ExportResult:
    """
    Perform the export operation.

    If apply=False, creates the export, shows diff, then CLEANS UP.
    If apply=True, commits the changes locally and keeps worktree for pushing.

    Never pushes - that's always left to the user.
    """
    config = ctx.config

    # Record the current main branch SHA for diff comparison
    old_main_sha = ctx.get_commit_sha(config.target_branch)
    info(f"Current {config.target_branch} is at: {old_main_sha[:12]}")

    # Create temporary directory for worktree
    worktree_dir = Path(tempfile.mkdtemp(prefix=WORKTREE_PREFIX))
    ctx.worktree_path = worktree_dir

    # Register cleanup handler for unexpected exits
    def cleanup_on_exit():
        if not apply and worktree_dir.exists():
            ctx.cleanup_worktree(worktree_dir, silent=True)

    atexit.register(cleanup_on_exit)

    info(f"Creating worktree at: {worktree_dir}")

    try:
        # Create worktree for main branch
        ctx.run_git("worktree", "add", str(worktree_dir), config.target_branch)
        success(f"Created worktree for '{config.target_branch}'")

        # Clear the worktree (except .git)
        info("Clearing existing content...")
        removed_count = clear_directory(worktree_dir, keep=(".git",))
        info(f"Removed {removed_count} existing items")

        # Copy directories
        total_files = 0
        for source_dir, dest_dir in config.directory_mappings:
            source_path = ctx.repo_root / source_dir
            dest_path = worktree_dir / dest_dir

            info(f"Copying {source_dir}/ → {dest_dir}/")
            file_count = copy_with_structure(source_path, dest_path, ctx)
            total_files += file_count
            info(f"  Copied {file_count} files")

        # Copy individual files
        for source_file, dest_file in config.file_mappings:
            source_path = ctx.repo_root / source_file
            dest_path = worktree_dir / dest_file

            info(f"Copying {source_file}")
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            total_files += 1

        # Generate special files
        info("Generating README.md for main branch")
        readme_path = worktree_dir / "README.md"
        readme_path.write_text(generate_main_readme(ctx))
        total_files += 1

        info("Generating CONTRIBUTING.md for main branch")
        contributing_path = worktree_dir / "CONTRIBUTING.md"
        contributing_path.write_text(generate_main_contributing(ctx))
        total_files += 1

        success(f"Exported {total_files} files total")

        # Stage all changes
        ctx.run_git("add", "-A", cwd=worktree_dir)

        # Check if there are any changes
        status_result = ctx.run_git("status", "--porcelain", cwd=worktree_dir)
        has_changes = bool(status_result.stdout.strip())

        if not has_changes:
            info("No changes detected - main branch is already up to date")
            diff_stat = "(no changes)"
            commit_sha = None
            commit_created = False
        else:
            # Get diff statistics
            diff_result = ctx.run_git(
                "diff", "--cached", "--stat", "--stat-width=80",
                cwd=worktree_dir
            )
            diff_stat = diff_result.stdout.strip()

            if apply:
                # Get the current develop commit for the message
                develop_sha = ctx.get_commit_sha(config.source_branch)

                # Create commit
                commit_msg = (
                    f"Export from {config.source_branch} ({develop_sha[:12]})\n\n"
                    f"Automated export using ucexport tool.\n"
                    f"Source: {config.source_branch} @ {develop_sha}\n"
                )

                ctx.run_git(
                    "commit", "-m", commit_msg,
                    cwd=worktree_dir
                )

                # Get commit SHA from worktree
                commit_sha = ctx.get_commit_sha("HEAD", cwd=worktree_dir)

                success(f"Created commit: {commit_sha[:12]}")
                commit_created = True
            else:
                commit_sha = None
                commit_created = False

        result = ExportResult(
            worktree_path=worktree_dir,
            files_copied=total_files,
            files_removed=removed_count,
            commit_created=commit_created,
            commit_sha=commit_sha,
            old_main_sha=old_main_sha,
            diff_stat=diff_stat,
            has_changes=has_changes,
        )

        # Always clean up worktree - it has served its purpose
        # The commit (if created) is already on the main branch ref
        if not apply:
            info("Preview mode - cleaning up worktree...")
        else:
            info("Cleaning up worktree...")
        ctx.cleanup_worktree(worktree_dir, silent=True)
        success("Worktree cleaned up")

        return result

    except Exception:
        # Clean up worktree on error
        ctx.cleanup_worktree(worktree_dir, silent=True)
        raise
    finally:
        # Unregister atexit handler since we handled cleanup
        try:
            atexit.unregister(cleanup_on_exit)
        except Exception:
            pass


# =============================================================================
# User interface
# =============================================================================

def print_diff_summary(result: ExportResult, ctx: GitContext) -> None:
    """Print a summary of the changes."""
    print("\n" + "=" * 70)
    print("EXPORT SUMMARY")
    print("=" * 70)

    if not result.has_changes:
        print("\n✅ No changes - main branch is already in sync with develop.\n")
        return

    print(f"\nFiles copied:  {result.files_copied}")
    print(f"Items removed: {result.files_removed}")
    print(f"\nDiff statistics:")
    print("-" * 40)
    print(result.diff_stat)
    print("-" * 40)


def print_next_steps(result: ExportResult, ctx: GitContext, apply: bool) -> None:
    """Print instructions for next steps."""
    config = ctx.config

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)

    if not result.has_changes:
        print("\nNothing to do - main is already up to date.")
        return

    if not apply:
        # Preview mode - worktree was cleaned up
        print(f"""
The export preview showed the changes that would be made.
The worktree has been cleaned up automatically.

To apply the changes (creates a commit locally):

    uv run ucexport --apply

This will:
1. Re-create the export
2. Commit the changes to '{config.target_branch}' locally
3. Show you how to push when ready
""")
    else:
        # Applied - show how to verify and push
        print(f"""
✅ Changes have been committed locally on '{config.target_branch}'.

To verify before pushing:

    git log {config.target_branch} -1              # See the commit
    git show {config.target_branch}                # See full diff
    git diff {result.old_main_sha[:12]}..{config.target_branch}  # Compare to old main

To push to GitHub:

    git push origin {config.target_branch}

To undo (reset to remote state):

    git fetch origin
    git branch -f {config.target_branch} origin/{config.target_branch}
""")


def do_cleanup(ctx: GitContext) -> int:
    """Clean up all ucexport worktrees."""
    print("=" * 70)
    print("UCEXPORT CLEANUP")
    print("=" * 70)

    worktrees = ctx.find_ucexport_worktrees()

    if not worktrees:
        print("\n✅ No ucexport worktrees found. Nothing to clean up.")
        return ExitCode.SUCCESS.value

    print(f"\nFound {len(worktrees)} ucexport worktree(s):")
    for path, branch in worktrees:
        print(f"  - {path} (branch: {branch or 'unknown'})")

    cleaned = ctx.cleanup_all_ucexport_worktrees()

    if cleaned > 0:
        success(f"\nCleaned up {cleaned} worktree(s)")
    else:
        warn("\nNo worktrees were cleaned (they may be in use or already removed)")

    return ExitCode.SUCCESS.value


# =============================================================================
# Entry point
# =============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Export curated content from develop to main branch.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    uv run ucexport              # Preview export (no side effects)
    uv run ucexport --apply      # Apply changes locally
    uv run ucexport --cleanup    # Remove stale worktrees

The tool never pushes automatically. After --apply, you must manually
push to GitHub after reviewing the changes.
        """,
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (create commit locally). Without this, only previews.",
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up any stale worktrees from previous runs and exit.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts.",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        # Find repository root
        repo_root = Path.cwd()
        while repo_root != repo_root.parent:
            if (repo_root / ".git").exists():
                break
            repo_root = repo_root.parent
        else:
            die("Not in a git repository", ExitCode.PRECONDITION_FAILED)

        # Create context
        ctx = GitContext(repo_root=repo_root)

        # Handle cleanup-only mode
        if args.cleanup:
            return do_cleanup(ctx)

        print("=" * 70)
        print("UCEXPORT - Export develop branch content to main")
        print("=" * 70)

        # Check preconditions (this also cleans up stale worktrees)
        check_preconditions(ctx, cleanup_existing=True)

        # Confirm with user
        if args.apply and not args.force:
            print("\n⚠️  This will create a commit on the main branch (locally).")
            response = input("Continue? [y/N] ").strip().lower()
            if response not in ("y", "yes"):
                print("Aborted by user.")
                return ExitCode.USER_ABORT.value

        # Perform export
        result = perform_export(ctx, apply=args.apply)

        # Print summary and next steps
        print_diff_summary(result, ctx)
        print_next_steps(result, ctx, args.apply)

        return ExitCode.SUCCESS.value

    except PreconditionError as e:
        die(str(e), ExitCode.PRECONDITION_FAILED)
    except GitError as e:
        die(str(e), ExitCode.GIT_ERROR)
    except KeyboardInterrupt:
        print("\n\nAborted by user.")
        return ExitCode.USER_ABORT.value
    except Exception as e:
        die(f"Unexpected error: {e}", ExitCode.UNEXPECTED_ERROR)


if __name__ == "__main__":
    sys.exit(main())
