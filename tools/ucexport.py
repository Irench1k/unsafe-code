#!/usr/bin/env python3
"""
ucexport - Export curated content from develop to main branch.

This tool synchronizes a student-friendly subset of the develop branch to main.
It uses git worktree for safe, isolated operations and provides human oversight
before any changes are pushed.

Usage:
    uv run ucexport          # Preview what would be exported
    uv run ucexport --apply  # Apply changes locally (still requires manual push)

The tool will:
1. Create a temporary git worktree for the main branch
2. Clear all existing content (except .git)
3. Copy the curated export from develop
4. Show a diff of changes
5. Provide commands for verification and pushing

Safety features:
- Never pushes automatically - requires explicit user action
- Uses git worktree for isolation - develop branch is never modified
- Validates all preconditions before any destructive operations
- Provides clear error messages and recovery instructions
"""

from __future__ import annotations

import argparse
import os
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

    def get_commit_sha(self, ref: str) -> str:
        """Get the full SHA of a ref."""
        result = self.run_git("rev-parse", ref)
        return result.stdout.strip()

    def branch_exists(self, branch: str) -> bool:
        """Check if a branch exists."""
        result = self.run_git(
            "rev-parse", "--verify", f"refs/heads/{branch}",
            check=False
        )
        return result.returncode == 0

    def remote_branch_exists(self, remote: str, branch: str) -> bool:
        """Check if a remote branch exists."""
        result = self.run_git(
            "ls-remote", "--heads", remote, branch,
            check=False
        )
        return bool(result.stdout.strip())

    def is_working_tree_clean(self) -> bool:
        """Check if the working tree is clean."""
        result = self.run_git("status", "--porcelain")
        return not result.stdout.strip()

    def list_worktrees(self) -> list[Path]:
        """List all existing worktrees."""
        result = self.run_git("worktree", "list", "--porcelain")
        worktrees = []
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                worktrees.append(Path(line[9:]))
        return worktrees


# =============================================================================
# Precondition checks
# =============================================================================

def check_preconditions(ctx: GitContext) -> None:
    """Validate all preconditions before proceeding."""
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

    # 7. Check for existing worktree conflicts
    worktrees = ctx.list_worktrees()
    for wt in worktrees:
        if wt != ctx.repo_root:
            # Check if it's for main branch
            try:
                result = ctx.run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt, check=False)
                if result.returncode == 0 and result.stdout.strip() == ctx.config.target_branch:
                    raise PreconditionError(
                        f"A worktree for '{ctx.config.target_branch}' already exists at: {wt}\n"
                        f"Remove it first with: git worktree remove {wt}"
                    )
            except Exception:
                pass  # Ignore errors checking worktree state

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

    If apply=False, creates the export but doesn't commit.
    If apply=True, commits the changes locally.

    Never pushes - that's always left to the user.
    """
    config = ctx.config

    # Record the current main branch SHA for diff comparison
    old_main_sha = ctx.get_commit_sha(config.target_branch)
    info(f"Current {config.target_branch} is at: {old_main_sha[:12]}")

    # Create temporary directory for worktree
    worktree_dir = Path(tempfile.mkdtemp(prefix="ucexport-main-"))
    ctx.worktree_path = worktree_dir

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

                commit_sha = ctx.get_commit_sha("HEAD", )
                # Get commit from worktree
                result = ctx.run_git("rev-parse", "HEAD", cwd=worktree_dir)
                commit_sha = result.stdout.strip()

                success(f"Created commit: {commit_sha[:12]}")
                commit_created = True
            else:
                commit_sha = None
                commit_created = False

        return ExportResult(
            worktree_path=worktree_dir,
            files_copied=total_files,
            files_removed=removed_count,
            commit_created=commit_created,
            commit_sha=commit_sha,
            old_main_sha=old_main_sha,
            diff_stat=diff_stat,
            has_changes=has_changes,
        )

    except Exception as e:
        # Clean up worktree on error
        cleanup_worktree(ctx, worktree_dir)
        raise


def cleanup_worktree(ctx: GitContext, worktree_path: Path) -> None:
    """Clean up a worktree safely."""
    try:
        ctx.run_git("worktree", "remove", "--force", str(worktree_path), check=False)
    except Exception:
        pass  # Best effort cleanup

    # Also try to remove the directory if it still exists
    try:
        if worktree_path.exists():
            shutil.rmtree(worktree_path)
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
        print(f"\nTo clean up the worktree:\n")
        print(f"    git worktree remove {result.worktree_path}")
        return

    if not apply:
        # Preview mode - show how to apply
        print(f"""
The export has been prepared in the worktree but NOT committed.

To review the changes:

    cd {result.worktree_path}
    git diff --cached           # See what will be committed
    git diff --cached --stat    # Summary view

To apply the changes (creates a commit locally):

    uv run ucexport --apply

To abort and clean up:

    git worktree remove {result.worktree_path}
""")
    else:
        # Applied - show how to verify and push
        print(f"""
✅ Changes have been committed locally on '{config.target_branch}'.

The commit exists in the worktree at: {result.worktree_path}

To verify before pushing:

    # Option 1: Check out main in the worktree
    cd {result.worktree_path}
    git log -1                  # See the commit
    git diff {result.old_main_sha[:12]}..HEAD     # Full diff from old main
    docker compose up -d        # Test the app

    # Option 2: Check out main in the main repo
    cd {ctx.repo_root}
    git checkout {config.target_branch}
    # (The commit is already there via the worktree)

To push to GitHub:

    cd {result.worktree_path}
    git push origin {config.target_branch}

    # Or from main repo:
    cd {ctx.repo_root}
    git push origin {config.target_branch}

To abort (discard the commit):

    git worktree remove --force {result.worktree_path}
    git checkout {config.target_branch}
    git reset --hard origin/{config.target_branch}

After pushing successfully, clean up:

    git worktree remove {result.worktree_path}
""")


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
    uv run ucexport              # Preview export (no changes)
    uv run ucexport --apply      # Apply changes locally

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
        "--force",
        action="store_true",
        help="Skip confirmation prompts.",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    print("=" * 70)
    print("UCEXPORT - Export develop branch content to main")
    print("=" * 70)

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

        # Check preconditions
        check_preconditions(ctx)

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
