"""Updated CLI using refactored components."""

from __future__ import annotations

import sys
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
    write_index
)
from .markdown_generator import generate_readme
from .readme_spec import load_readme_spec


app = typer.Typer(add_completion=False, help="Unsafe Docs Generator (Refactored)")
console = Console()


def find_readme_yml_paths(root: Path) -> List[Path]:
    """Find all readme.yml files in the project."""
    return find_files_by_name(root, "readme.yml")


@app.command()
def list_targets(
    root: str = typer.Argument(str(Path.cwd())),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """List all readme.yml targets found in the project."""
    base = Path(root)
    paths = find_readme_yml_paths(base)
    
    table = Table(title="readme.yml targets")
    table.add_column("#")
    table.add_column("Path")
    
    for idx, p in enumerate(paths, start=1):
        table.add_row(str(idx), str(p))
    
    console.print(table)
    
    if verbose:
        print(f"[cyan]Found {len(paths)} target(s) under {base}[/cyan]")


@app.command()
def index(
    root: str = typer.Argument(str(Path.cwd())),
    target: Optional[str] = typer.Option(None, help="Path to a specific readme.yml or its directory"),
    write: bool = typer.Option(True, help="Write index.yml to target directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write any files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Generate index.yml files from source code annotations."""
    base = Path(root)
    
    # Determine target directories
    if target:
        tpath = Path(target)
        yml_path = tpath if tpath.name == "readme.yml" else tpath / "readme.yml"
        if not yml_path.exists():
            console.print(f"[red]readme.yml not found at {yml_path}[/red]")
            raise typer.Exit(code=1)
        dirs = [yml_path.parent]
    else:
        dirs = [p.parent for p in find_readme_yml_paths(base)]

    # Process each directory
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


@app.command()
def generate(
    root: str = typer.Argument(str(Path.cwd())),
    target: Optional[str] = typer.Option(None, help="Path to a specific readme.yml or its directory"),
    force: bool = typer.Option(False, help="Force README.md regeneration even if cache matches"),
    backup: bool = typer.Option(True, help="Backup README.md before overwriting"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write any files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Generate README.md files from index data."""
    base = Path(root)
    
    # Determine target directories
    if target:
        tpath = Path(target)
        yml_path = tpath if tpath.name == "readme.yml" else tpath / "readme.yml"
        if not yml_path.exists():
            console.print(f"[red]readme.yml not found at {yml_path}[/red]")
            raise typer.Exit(code=1)
        dirs = [yml_path.parent]
    else:
        dirs = [p.parent for p in find_readme_yml_paths(base)]

    # Process each directory
    for d in dirs:
        try:
            readme_yml = d / "readme.yml"
            spec = load_readme_spec(readme_yml)
            
            # Check if we need to regenerate
            idx_existing = read_existing_index(d / "index.yml")
            idx = build_directory_index(d, spec)
            
            if (idx_existing and 
                not force and 
                idx_existing.build_signature == idx.build_signature and 
                idx_existing.last_readme_fingerprint):
                print(f"[yellow]Skipped (no changes):[/yellow] {d}")
                continue

            # Write/refresh index
            if not dry_run:
                write_index(d / "index.yml", idx)

            # Load structure from readme.yml
            import yaml
            with open(readme_yml, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            structure = data.get("structure", [])
            
            # Generate README content
            readme_content = generate_readme(idx, spec.title, spec.intro, structure)

            # Write README
            readme_path = d / "README.md"
            if backup and not dry_run and readme_path.exists():
                backup_file(readme_path)
                
            if not dry_run:
                write_text(readme_path, readme_content)

            # Update fingerprint to allow skip next time
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


@app.command()
def run_all(
    root: str = typer.Argument(str(Path.cwd())),
    force: bool = typer.Option(False, help="Force regeneration of all targets"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not write any files"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run indexing and generation for all targets."""
    base = Path(root)
    dirs = [p.parent for p in find_readme_yml_paths(base)]
    
    for d in dirs:
        # Index first
        try:
            index(
                root=root, 
                target=str(d), 
                write=True, 
                dry_run=dry_run, 
                verbose=verbose
            )
        except Exception as e:
            console.print(f"[red]Indexing failed for {d}: {e}[/red]")
            continue
            
        # Then generate
        try:
            generate(
                root=root,
                target=str(d),
                force=force,
                backup=True,
                dry_run=dry_run,
                verbose=verbose
            )
        except Exception as e:
            console.print(f"[red]Generation failed for {d}: {e}[/red]")


@app.command()
def test(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose test output"),
):
    """Run tests for the unsafe_docs package."""
    import unittest
    import sys
    from pathlib import Path
    
    # Add the tests directory to the path
    tests_dir = Path(__file__).parent / "tests"
    if tests_dir.exists():
        sys.path.insert(0, str(tests_dir.parent))
        
        # Discover and run tests
        loader = unittest.TestLoader()
        suite = loader.discover(str(tests_dir), pattern='test_*.py')
        
        verbosity = 2 if verbose else 1
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)
        
        if not result.wasSuccessful():
            raise typer.Exit(code=1)
    else:
        console.print("[yellow]No tests directory found[/yellow]")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
