#!/usr/bin/env python3
"""
uclint - E2E spec suite linter for httpyac test files

Identifies issues in the spec suite:
- Jurisdiction violations: HTTP requests outside directory path
- Method violations: HTTP method doesn't match directory verb
- File length warnings: Files exceeding 100 lines
- Test count warnings: Files with more than 8 tests
- Fake tests: Test sections with only JavaScript, no HTTP request

Suppression directive:
  # @ucskip              - Suppress all checks for this test/request
  # @ucskip endpoint     - Suppress endpoint jurisdiction check only
  # @ucskip method       - Suppress method mismatch check only
  # @ucskip fake-test    - Suppress fake test warning

Usage:
  uclint                 # Lint spec/v301 (default)
  uclint v302            # Lint specific version
  uclint --all           # Lint all versions
  uclint --strict        # Exit non-zero on any issue
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# =============================================================================
# Constants
# =============================================================================

# HTTP method pattern for detecting requests
HTTP_METHOD_PATTERN = re.compile(
    r"^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(/\S*)", re.IGNORECASE | re.MULTILINE
)

# Test section delimiter
TEST_HEADER_PATTERN = re.compile(r"^###\s+(.+)$", re.MULTILINE)

# JavaScript block patterns
JS_BLOCK_PATTERN = re.compile(r"\{\{[\s\S]*?\}\}")
JS_ASSERT_PATTERN = re.compile(r"^\?\?\s+js\s+", re.MULTILINE)

# Suppression directive pattern: # @ucskip [type1] [type2] ...
UCSKIP_PATTERN = re.compile(r"#\s*@ucskip(?:\s+(\S.*))?$")

# Name annotation pattern
NAME_PATTERN = re.compile(r"#\s*@name\s+(\S+)")

# Files to skip
SKIP_PATTERNS = {"_imports.http", "_fixtures.http"}

# Limits
LINE_LIMIT = 100
TEST_LIMIT = 8


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Violation:
    """A jurisdiction or method violation"""

    file: Path
    line: int
    request: str
    reason: str  # "endpoint", "method", or "method+endpoint"


@dataclass
class FileWarning:
    """A file-level warning (length or test count)"""

    file: Path
    message: str


@dataclass
class FakeTest:
    """A test section with only JavaScript, no HTTP request"""

    file: Path
    line: int
    name: str


@dataclass
class LintResult:
    """Complete lint results for a version"""

    violations: list[Violation] = field(default_factory=list)
    warnings: list[FileWarning] = field(default_factory=list)
    fake_tests: list[FakeTest] = field(default_factory=list)
    files_scanned: int = 0


# =============================================================================
# Path Utilities
# =============================================================================


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
    current = start_path.resolve()
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            if (current / "spec" / "spec.yml").exists():
                return current / "spec"
        current = current.parent

    return None


def dir_to_endpoint(dir_path: str) -> tuple[str, str]:
    """
    Convert directory path to expected endpoint and method.

    cart/checkout/post -> ("cart/checkout", "POST")
    orders/refund-status/patch -> ("orders/refund-status", "PATCH")
    orders/list/get -> ("orders", "GET")  # Special case: list -> root
    """
    parts = Path(dir_path).parts
    if len(parts) < 2:
        return "", ""

    verb = parts[-1].upper()
    resource_parts = parts[:-1]

    # Special case: "list" action means the root resource
    if len(resource_parts) >= 1 and resource_parts[-1] == "list":
        resource_parts = resource_parts[:-1]

    resource = "/".join(resource_parts)
    return resource, verb


def url_to_endpoint(url: str) -> str:
    """
    Normalize URL to comparable endpoint form.

    /cart/{{id}}/checkout -> cart/checkout
    /orders/{{id}}/refund/status -> orders/refund/status
    /orders?... -> orders
    """
    # Remove leading slash
    url = url.lstrip("/")
    # Remove query params
    url = url.split("?")[0]
    # Remove template vars but keep path structure
    url = re.sub(r"\{\{[^}]*\}\}", "", url)
    # Normalize multiple slashes
    url = re.sub(r"/+", "/", url)
    # Remove trailing slash
    url = url.rstrip("/")
    return url


def matches_endpoint(dir_endpoint: str, url_endpoint: str) -> bool:
    """
    Check if URL matches the directory's expected endpoint.

    Handles hyphenated dirs: refund-status -> refund/status
    """
    # Normalize hyphenated dirs
    normalized_dir = dir_endpoint.replace("-", "/")

    # Direct match
    if url_endpoint == normalized_dir:
        return True

    # URL extends directory (e.g., POST /orders/{id}/refund matches orders/refund)
    if url_endpoint.startswith(normalized_dir + "/"):
        return True

    # Directory is more specific than URL
    if normalized_dir.startswith(url_endpoint + "/"):
        return True

    # Check without the transformation too
    if url_endpoint == dir_endpoint:
        return True

    return False


# =============================================================================
# Suppression Logic
# =============================================================================


def find_ucskip(lines: list[str], line_idx: int) -> set[str]:
    """
    Look for @ucskip directives in preceding lines (up to 5 lines back).

    Returns set of suppression types: {"endpoint", "method", "fake-test", "all"}
    Empty set means no suppression.
    """
    suppressions: set[str] = set()

    # Look up to 5 lines back
    start = max(0, line_idx - 5)
    for i in range(line_idx - 1, start - 1, -1):
        line = lines[i]

        # Check for @ucskip
        match = UCSKIP_PATTERN.search(line)
        if match:
            types = match.group(1)
            if types is None or types.strip() == "":
                # Bare @ucskip suppresses all
                suppressions.add("all")
            else:
                # Parse individual types
                for t in types.split():
                    suppressions.add(t.lower())

        # Stop if we hit a non-comment, non-blank, non-@ line
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("@"):
            break

    return suppressions


def is_suppressed(suppressions: set[str], check_type: str) -> bool:
    """Check if a specific check type is suppressed."""
    return "all" in suppressions or check_type in suppressions


# =============================================================================
# Linting Logic
# =============================================================================


def lint_file_jurisdiction(
    file_path: Path, content: str, dir_path: str
) -> list[Violation]:
    """Check for jurisdiction and method violations in a file."""
    violations = []
    lines = content.split("\n")

    expected_endpoint, expected_method = dir_to_endpoint(dir_path)
    if not expected_endpoint:
        return violations

    for match in HTTP_METHOD_PATTERN.finditer(content):
        method = match.group(1).upper()
        url = match.group(2)
        url_endpoint = url_to_endpoint(url)

        # Find line number (1-indexed)
        line_start = content[: match.start()].count("\n")
        line_num = line_start + 1

        # Check for suppression
        suppressions = find_ucskip(lines, line_start)

        method_violation = False
        endpoint_violation = False

        # Check method mismatch
        if method != expected_method:
            if not is_suppressed(suppressions, "method"):
                method_violation = True

        # Check endpoint mismatch
        if not matches_endpoint(expected_endpoint, url_endpoint):
            if not is_suppressed(suppressions, "endpoint"):
                endpoint_violation = True

        # Build reason string
        if method_violation and endpoint_violation:
            reason = "method+endpoint"
        elif method_violation:
            reason = "method"
        elif endpoint_violation:
            reason = "endpoint"
        else:
            continue

        violations.append(
            Violation(
                file=file_path,
                line=line_num,
                request=f"{method} {url}",
                reason=reason,
            )
        )

    return violations


def lint_file_size(file_path: Path, content: str) -> list[FileWarning]:
    """Check file length and test count."""
    warnings = []
    lines = content.split("\n")
    line_count = len(lines)

    if line_count > LINE_LIMIT:
        warnings.append(
            FileWarning(
                file=file_path,
                message=f"{line_count} lines (limit: {LINE_LIMIT})",
            )
        )

    # Count test sections (### headers)
    test_count = len(TEST_HEADER_PATTERN.findall(content))
    if test_count > TEST_LIMIT:
        warnings.append(
            FileWarning(
                file=file_path,
                message=f"{test_count} tests (limit: {TEST_LIMIT})",
            )
        )

    return warnings


def lint_fake_tests(file_path: Path, content: str) -> list[FakeTest]:
    """
    Find test sections that contain only JavaScript with no HTTP request.

    A test section is "fake" if:
    1. Starts with ### header
    2. Contains {{ ... }} JavaScript block(s) or ?? js assertions
    3. Does NOT contain an HTTP method line
    """
    fake_tests = []
    lines = content.split("\n")

    # Find all test section boundaries
    test_starts: list[tuple[int, str]] = []  # (line_idx, name)
    for i, line in enumerate(lines):
        match = TEST_HEADER_PATTERN.match(line)
        if match:
            test_starts.append((i, match.group(1).strip()))

    if not test_starts:
        return fake_tests

    # Process each test section
    for idx, (start_line, header_name) in enumerate(test_starts):
        # Determine end of this section
        if idx + 1 < len(test_starts):
            end_line = test_starts[idx + 1][0]
        else:
            end_line = len(lines)

        section_content = "\n".join(lines[start_line:end_line])

        # Check for suppression in section
        suppressions: set[str] = set()
        for i in range(start_line, min(start_line + 10, end_line)):
            match = UCSKIP_PATTERN.search(lines[i])
            if match:
                types = match.group(1)
                if types is None or types.strip() == "":
                    suppressions.add("all")
                else:
                    for t in types.split():
                        suppressions.add(t.lower())

        if is_suppressed(suppressions, "fake-test"):
            continue

        # Check for JavaScript content
        has_js = bool(JS_BLOCK_PATTERN.search(section_content)) or bool(
            JS_ASSERT_PATTERN.search(section_content)
        )

        # Check for HTTP request
        has_http = bool(HTTP_METHOD_PATTERN.search(section_content))

        # Find @name if present
        name_match = NAME_PATTERN.search(section_content)
        test_name = name_match.group(1) if name_match else header_name

        # It's a fake test if it has JS but no HTTP request
        if has_js and not has_http:
            fake_tests.append(
                FakeTest(
                    file=file_path,
                    line=start_line + 1,  # 1-indexed
                    name=test_name,
                )
            )

    return fake_tests


def should_skip_file(path: Path) -> bool:
    """Check if a file should be skipped."""
    name = path.name
    # Skip infrastructure files
    if name in SKIP_PATTERNS or name.startswith("_"):
        return True
    # Skip inherited files
    if name.startswith("~"):
        return True
    return False


def lint_version(version_dir: Path) -> LintResult:
    """Lint all .http files in a version directory."""
    result = LintResult()

    if not version_dir.exists():
        return result

    for http_file in sorted(version_dir.rglob("*.http")):
        if should_skip_file(http_file):
            continue

        result.files_scanned += 1

        try:
            content = http_file.read_text()
        except (OSError, UnicodeDecodeError) as e:
            result.warnings.append(FileWarning(file=http_file, message=f"Read error: {e}"))
            continue

        # Get relative directory path from version root
        rel_path = http_file.relative_to(version_dir)
        dir_path = str(rel_path.parent)

        # Run checks
        result.violations.extend(lint_file_jurisdiction(http_file, content, dir_path))
        result.warnings.extend(lint_file_size(http_file, content))
        result.fake_tests.extend(lint_fake_tests(http_file, content))

    return result


# =============================================================================
# Output
# =============================================================================


def print_results(
    console: Console, version_name: str, result: LintResult, version_dir: Path
) -> None:
    """Print lint results using Rich formatting."""
    # Header
    console.print()
    console.print(
        Panel(
            f"[bold]E2E Spec Lint: {version_name}[/bold]",
            expand=False,
        )
    )
    console.print()

    has_issues = result.violations or result.fake_tests or result.warnings

    def rel_path(file: Path) -> str:
        """Get relative path from version directory."""
        try:
            return str(file.relative_to(version_dir))
        except ValueError:
            return str(file)

    # Jurisdiction Violations
    if result.violations:
        console.print("[bold red]Jurisdiction Violations[/bold red]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Line", justify="right")
        table.add_column("Request")
        table.add_column("Issue", style="yellow")

        for v in result.violations:
            table.add_row(rel_path(v.file), str(v.line), v.request, f"[{v.reason}]")

        console.print(table)
        console.print()

    # Fake Tests
    if result.fake_tests:
        console.print("[bold yellow]Fake Tests[/bold yellow] [dim](JS-only, no HTTP request)[/dim]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Line", justify="right")
        table.add_column("Test Name")

        for ft in result.fake_tests:
            table.add_row(rel_path(ft.file), str(ft.line), ft.name)

        console.print(table)
        console.print()

    # File Warnings
    if result.warnings:
        console.print("[bold yellow]File Warnings[/bold yellow]")
        table = Table(show_header=True, header_style="bold")
        table.add_column("File", style="cyan", no_wrap=True)
        table.add_column("Issue")

        for w in result.warnings:
            table.add_row(rel_path(w.file), w.message)

        console.print(table)
        console.print()

    # Summary
    if has_issues:
        console.print(
            f"[bold]Summary:[/bold] "
            f"[red]{len(result.violations)} violation(s)[/red], "
            f"[yellow]{len(result.fake_tests)} fake test(s)[/yellow], "
            f"[yellow]{len(result.warnings)} warning(s)[/yellow] "
            f"in {result.files_scanned} files"
        )
    else:
        console.print(
            f"[bold green]All clear![/bold green] "
            f"Scanned {result.files_scanned} files, no issues found."
        )


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="uclint",
        description="Lint E2E spec suite for common issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uclint                 Lint spec/v301 (default)
  uclint v302            Lint specific version
  uclint --all           Lint all versions
  uclint --strict        Exit non-zero on any issue

Suppression:
  Add directives in comments above HTTP request lines:
    # @ucskip              Suppress all checks
    # @ucskip endpoint     Suppress endpoint mismatch only
    # @ucskip method       Suppress method mismatch only
    # @ucskip fake-test    Suppress fake test warning

Checks:
  - Jurisdiction: HTTP requests must match directory endpoint
  - Method: HTTP method must match directory verb (get/post/patch/etc)
  - File length: Files should not exceed 100 lines
  - Test count: Files should not have more than 8 test sections
  - Fake tests: Test sections should have HTTP requests, not just JavaScript
""",
    )

    parser.add_argument(
        "versions",
        nargs="*",
        metavar="VERSION",
        help="Version(s) to lint (default: v301)",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Lint all versions",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on any issue (violations, fake tests, or warnings)",
    )
    parser.add_argument(
        "--spec-dir",
        type=Path,
        help="Path to spec directory (default: auto-detect)",
    )

    args = parser.parse_args()

    console = Console()

    # Find spec directory
    spec_dir = args.spec_dir or find_spec_dir()
    if not spec_dir:
        console.print("[bold red]Error:[/bold red] Could not find spec directory")
        console.print(f"Searched from: {Path.cwd()}")
        return 1

    # Determine versions to lint
    if args.all:
        # Find all version directories
        versions = sorted(
            [
                d.name
                for d in spec_dir.iterdir()
                if d.is_dir() and d.name.startswith("v") and d.name[1:].isdigit()
            ]
        )
    elif args.versions:
        versions = args.versions
    else:
        versions = ["v301"]  # Default

    # Lint each version
    total_result = LintResult()
    for version in versions:
        version_dir = spec_dir / version
        if not version_dir.exists():
            console.print(f"[bold yellow]Warning:[/bold yellow] {version} not found, skipping")
            continue

        result = lint_version(version_dir)
        print_results(console, version, result, version_dir)

        # Accumulate totals
        total_result.violations.extend(result.violations)
        total_result.warnings.extend(result.warnings)
        total_result.fake_tests.extend(result.fake_tests)
        total_result.files_scanned += result.files_scanned

    # Exit code
    if args.strict:
        if total_result.violations or total_result.fake_tests or total_result.warnings:
            return 1

    # Always fail on violations
    if total_result.violations:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
