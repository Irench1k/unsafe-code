"""CLI for the docs generator."""

from pathlib import Path

import typer
from rich import print
from rich.console import Console
from rich.table import Table

from .fs_utils import backup_file, compute_fingerprint, find_files_by_name, sha256_file, write_text
from .indexer import (
    build_directory_index,
    read_existing_index,
    write_index,
)
from .languages import assemble_code_from_parts
from .markdown_generator import generate_readme
from .readme_spec import load_readme_spec

app = typer.Typer(add_completion=True, help="Docs generator for Unsafe Code")
console = Console()


def _find_readme_yml_paths(root: Path) -> list[Path]:
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
    target: str | None = typer.Option(None, help="Path to a specific readme.yml or its directory"),
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

            # Avoid churn: only write if signature changed or file absent
            idx_existing = read_existing_index(d / "index.yml")
            if not dry_run and write:
                if not idx_existing or idx_existing.build_signature != idx.build_signature:
                    write_index(d / "index.yml", idx)
                else:
                    print(f"[yellow]Skipped (no changes):[/yellow] {d}")
                    if verbose:
                        print(f"  [dim]Signature:[/dim] {idx.build_signature}")
                    continue

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
    target: str | None = typer.Option(None, help="Path to a specific readme.yml or its directory"),
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

            # Include readme.yml content in the regeneration decision to avoid stale caches
            spec_hash = sha256_file(readme_yml)
            combined_readme_sig = compute_fingerprint([idx.build_signature or "", spec_hash])

            if (
                idx_existing
                and not force
                and idx_existing.build_signature == idx.build_signature
                and idx_existing.last_readme_fingerprint == combined_readme_sig
            ):
                print(f"[yellow]Skipped (no changes):[/yellow] {d}")
                continue

            if not dry_run:
                write_index(d / "index.yml", idx)

            # Use the parsed spec directly; ToC handled via spec.toc
            sections = [
                {"title": s.title, "description": s.description, "examples": s.examples}
                for s in spec.sections
            ]

            readme_content = generate_readme(
                idx,
                spec.title,
                spec.summary,
                spec.description,
                sections,
                spec.toc,
            )

            readme_path = d / "README.md"
            if backup and not dry_run and readme_path.exists():
                backup_file(readme_path)

            if not dry_run:
                write_text(readme_path, readme_content)

            # Persist the combined fingerprint that includes readme.yml content
            idx.last_readme_fingerprint = combined_readme_sig
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


@app.command(name="watch")
def watch_cmd(
    root: str = typer.Argument(str(Path.cwd())),
    target: str | None = typer.Option(None, help="Path to a specific readme.yml or its directory"),
    interval: float = typer.Option(1.0, help="Polling interval in seconds"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Continuously watch for changes and regenerate README.md files.

    This uses a lightweight polling strategy (no extra dependencies). It watches:
    - readme.yml content
    - example code and attachments captured by the index signature
    """
    import time

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

    if not dirs:
        console.print("[yellow]No readme.yml targets found to watch.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"[green]Watching {len(dirs)} target(s). Press Ctrl+C to stop.[/green]")
    last_fps: dict[Path, str] = {}

    try:
        while True:
            for d in dirs:
                try:
                    readme_yml = d / "readme.yml"
                    spec = load_readme_spec(readme_yml)
                    idx = build_directory_index(d, spec)
                    spec_hash = sha256_file(readme_yml)
                    fp = compute_fingerprint([idx.build_signature or "", spec_hash])
                    if last_fps.get(d) != fp:
                        if verbose:
                            print(f"[cyan]Change detected:[/cyan] {d}")
                        # Update index and README
                        index_cmd(root=root, target=str(d), write=True, dry_run=False, verbose=verbose)
                        generate_cmd(root=root, target=str(d), force=True, backup=True, dry_run=False, verbose=verbose)
                        last_fps[d] = fp
                except Exception as e:
                    console.print(f"[red]Watch error in {d}: {e}[/red]")
                    if verbose:
                        import traceback
                        traceback.print_exc()
            time.sleep(max(0.1, interval))
    except KeyboardInterrupt:
        console.print("\n[green]Stopped watching.[/green]")


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
            spec_hash = sha256_file(readme_yml)
            combined_readme_sig = compute_fingerprint([idx.build_signature or "", spec_hash])

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

            if idx_existing.last_readme_fingerprint != combined_readme_sig:
                print(f"[yellow]README not regenerated:[/yellow] {d}")
                if verbose:
                    print(f"  [dim]expected:[/dim] {combined_readme_sig}")
                    print(f"  [dim]actual:  [/dim] {idx_existing.last_readme_fingerprint}")
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


@app.command(name="show")
def show_cmd(
    example_id: int = typer.Argument(..., help="Example id to preview"),
    root: str = typer.Argument(str(Path.cwd())),
    target: str | None = typer.Option(None, help="Path to a specific readme.yml or its directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Preview a single example: metadata, parts, and assembled code."""
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

    if not dirs:
        console.print("[red]No readme.yml targets found.[/red]")
        raise typer.Exit(code=1)

    # Use the first directory by default when not specified
    d = dirs[0]
    try:
        spec = load_readme_spec(d / "readme.yml")
        idx = build_directory_index(d, spec)
        ex = idx.examples.get(int(example_id))
        if not ex:
            console.print(f"[red]Example {example_id} not found in {d}[/red]")
            raise typer.Exit(code=1)

        console.print(f"[bold]Example {ex.id}[/bold] — kind: {ex.kind}, lang: {ex.language or ''}")
        if ex.title:
            console.print(f"[bold]Title:[/bold] {ex.title}")
        if ex.notes:
            console.print(f"[bold]Notes:[/bold]\n{ex.notes}")
        if ex.http:
            console.print(f"[bold]HTTP:[/bold] {ex.http}")
        if ex.parts:
            console.print("[bold]Parts:[/bold]")
            for p in sorted(ex.parts, key=lambda p: p.part):
                rel = Path(p.file_path).relative_to(idx.root).as_posix()
                console.print(f"  - part {p.part}: {rel} [{p.code_start_line}-{p.code_end_line}]")
            code = assemble_code_from_parts(ex.parts)
            if code:
                console.print("\n[bold]Code:[/bold]")
                console.print(f"```{ex.language or ''}\n{code}\n```")
        else:
            console.print("[yellow]No parts/codespan resolved.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error showing example: {e}[/red]")
        if verbose:
            import traceback
            traceback.print_exc()
        raise typer.Exit(code=1) from e

def docs_main() -> None:
    app()
