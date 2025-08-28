"""CLI for the docs generator."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from .fs_utils import backup_file, find_files_by_name, write_text
from .indexer import (
    build_directory_index,
    read_existing_index,
    write_index,
)
from .markdown_generator import generate_readme
from .readme_spec import load_readme_spec


app = typer.Typer(add_completion=True, help="Docs generator for Unsafe Code")
console = Console()


def _find_readme_yml_paths(root: Path) -> List[Path]:
    return find_files_by_name(root, "readme.yml")


@app.command(name="list")
def list_cmd(
    root: str = typer.Argument(str(Path.cwd())),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """List all readme.yml targets found in the project."""
    base = Path(root)
    paths = _find_readme_yml_paths(base)

    table = Table(title="readme.yml targets")
    table.add_column("#")
    table.add_column("Path")

    for idx, p in enumerate(paths, start=1):
        table.add_row(str(idx), str(p))

    console.print(table)

    if verbose:
        print(f"[cyan]Found {len(paths)} target(s) under {base}[/cyan]")


@app.command(name="index")
def index_cmd(
    root: str = typer.Argument(str(Path.cwd())),
    target: Optional[str] = typer.Option(None, help="Path to a specific readme.yml or its directory"),
    write: bool = typer.Option(True, help="Write index.yml to target directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write any files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Generate index.yml files from source code annotations."""
    base = Path(root)

    if target:
        tpath = Path(target)
        yml_path = tpath if tpath.name == "readme.yml" else tpath / "readme.yml"
        if not yml_path.exists():
            console.print(f"[red]readme.yml not found at {yml_path}[/red]")
            raise typer.Exit(code=1)
        dirs = [yml_path.parent]
    else:
        dirs = [p.parent for p in _find_readme_yml_paths(base)]

    for d in dirs:
        try:
            spec = load_readme_spec(d / "readme.yml")
            idx = build_directory_index(d, spec)

            if not dry_run and write:
                write_index(d / "index.yml", idx)

            print(f"[green]Indexed:[/green] {d}")

            if verbose:
                print(f"  [dim]Examples:[/dim] {sorted(idx.examples.keys())}")
                print(f"  [dim]Build signature:[/dim] {idx.build_signature}")

        except Exception as e:
            console.print(f"[red]Error processing {d}: {e}[/red]")
            if verbose:
                import traceback
                traceback.print_exc()


@app.command(name="generate")
def generate_cmd(
    root: str = typer.Argument(str(Path.cwd())),
    target: Optional[str] = typer.Option(None, help="Path to a specific readme.yml or its directory"),
    force: bool = typer.Option(False, help="Force README.md regeneration even if cache matches"),
    backup: bool = typer.Option(True, help="Backup README.md before overwriting"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write any files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Generate README.md files from index data."""
    base = Path(root)

    if target:
        tpath = Path(target)
        yml_path = tpath if tpath.name == "readme.yml" else tpath / "readme.yml"
        if not yml_path.exists():
            console.print(f"[red]readme.yml not found at {yml_path}[/red]")
            raise typer.Exit(code=1)
        dirs = [yml_path.parent]
    else:
        dirs = [p.parent for p in _find_readme_yml_paths(base)]

    for d in dirs:
        try:
            readme_yml = d / "readme.yml"
            spec = load_readme_spec(readme_yml)

            idx_existing = read_existing_index(d / "index.yml")
            idx = build_directory_index(d, spec)

            if idx_existing and not force and idx_existing.build_signature == idx.build_signature and idx_existing.last_readme_fingerprint:
                print(f"[yellow]Skipped (no changes):[/yellow] {d}")
                continue

            if not dry_run:
                write_index(d / "index.yml", idx)

            from .yaml_io import read_yaml
            data = read_yaml(readme_yml)
            structure = data.get("structure", [])

            readme_content = generate_readme(idx, spec.title, spec.intro, structure)

            readme_path = d / "README.md"
            if backup and not dry_run and readme_path.exists():
                backup_file(readme_path)

            if not dry_run:
                write_text(readme_path, readme_content)

            idx.last_readme_fingerprint = idx.build_signature
            if not dry_run:
                write_index(d / "index.yml", idx)

            print(f"[green]Generated README:[/green] {readme_path}")

            if verbose:
                print(f"  [dim]Signature:[/dim] {idx.build_signature}")

        except Exception as e:
            console.print(f"[red]Error processing {d}: {e}[/red]")
            if verbose:
                import traceback
                traceback.print_exc()


@app.command(name="all")
def all_cmd(
    root: str = typer.Argument(str(Path.cwd())),
    force: bool = typer.Option(False, help="Force regeneration of all targets"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write any files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run indexing and generation for all targets."""
    base = Path(root)
    dirs = [p.parent for p in _find_readme_yml_paths(base)]

    for d in dirs:
        try:
            index_cmd(root=root, target=str(d), write=True, dry_run=dry_run, verbose=verbose)
        except Exception as e:
            console.print(f"[red]Indexing failed for {d}: {e}[/red]")
            continue

        try:
            generate_cmd(root=root, target=str(d), force=force, backup=True, dry_run=dry_run, verbose=verbose)
        except Exception as e:
            console.print(f"[red]Generation failed for {d}: {e}[/red]")


@app.command(name="test")
def test_cmd(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose test output"),
):
    """Run unit tests for the docs package."""
    import unittest
    loader = unittest.TestLoader()
    suite = loader.discover("tools/docs/tests", pattern="test_*.py")
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    raise typer.Exit(code=0 if result.wasSuccessful() else 1)


@app.command(name="verify")
def verify_cmd(
    root: str = typer.Argument(str(Path.cwd())),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Verify that index.yml and README.md are up-to-date (no writes)."""
    base = Path(root)
    dirs = [p.parent for p in _find_readme_yml_paths(base)]

    mismatches = 0
    for d in dirs:
        try:
            readme_yml = d / "readme.yml"
            spec = load_readme_spec(readme_yml)
            idx = build_directory_index(d, spec)

            idx_existing = read_existing_index(d / "index.yml")
            if not idx_existing:
                print(f"[red]Missing index.yml:[/red] {d}")
                mismatches += 1
                continue

            if idx_existing.build_signature != idx.build_signature:
                print(f"[yellow]Out of date index:[/yellow] {d}")
                if verbose:
                    print(f"  [dim]expected:[/dim] {idx.build_signature}")
                    print(f"  [dim]actual:  [/dim] {idx_existing.build_signature}")
                mismatches += 1
                continue

            if idx_existing.last_readme_fingerprint != idx.build_signature:
                print(f"[yellow]README not regenerated:[/yellow] {d}")
                if verbose:
                    print(f"  [dim]fingerprint:[/dim] {idx_existing.last_readme_fingerprint}")
                    print(f"  [dim]signature:  [/dim] {idx.build_signature}")
                mismatches += 1
                continue

            if verbose:
                print(f"[green]OK:[/green] {d}")

        except Exception as e:
            console.print(f"[red]Verification failed for {d}: {e}[/red]")
            if verbose:
                import traceback
                traceback.print_exc()
            mismatches += 1

    if mismatches:
        print("\n[red]Verification failed.[/red] Run: `uv run docs all -v`.")
        raise typer.Exit(code=1)
    else:
        print("[green]All targets up-to-date.[/green]")
        raise typer.Exit(code=0)

def docs_main() -> None:
    app()
