"""CodeQL-based code analysis backend.

Uses the CodeQL CLI to create databases and run queries for Flask
route detection, input access identification, and call graph extraction.
Requires the `codeql` CLI and auto-downloads the Python query pack on first use.

This backend adds value beyond the AST backend for:
- CodeQL's precise type inference and call resolution
- Taint tracking with library models for Flask/Werkzeug
- Rich data flow analysis through exception handlers and generators
"""

from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from pathlib import Path

from ..models import (
    AccessorKind,
    BeforeRequestFact,
    CallEdge,
    DictMergeFact,
    InputAccessFact,
    InputSource,
    Location,
    RouteFact,
    RouteKind,
)
from .augment import augment_with_ast
from .interface import ExtractionResult

_QUERIES_DIR = Path(__file__).parent / "codeql_queries"

_SOURCE_MAP = {
    "args": InputSource.ARGS,
    "form": InputSource.FORM,
    "values": InputSource.VALUES,
    "json": InputSource.JSON,
    "data": InputSource.DATA,
    "headers": InputSource.HEADERS,
    "cookies": InputSource.COOKIES,
    "files": InputSource.FILES,
}

_ACCESSOR_MAP = {
    "get": AccessorKind.GET,
    "getlist": AccessorKind.GETLIST,
    "index": AccessorKind.INDEX,
    "direct": AccessorKind.DIRECT,
}


def _fix_qualname(name: str, qualname: str, file: str) -> str:
    """Prepend the module path to a CodeQL qualname.

    CodeQL's ``getQualifiedName()`` returns names relative to the module
    (e.g. ``"create_new_order"`` or ``"ClassName.method"``).  The rest of
    the pipeline expects a fully-qualified dotted name with the module
    prefix (e.g. ``"routes.create_new_order"``).
    """
    if not file:
        return qualname or name
    parts = list(Path(file).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    module = ".".join(parts)
    base = qualname or name
    return f"{module}.{base}" if module else base


class CodeQLBackend:
    """CodeQL-based code analysis backend."""

    name = "codeql"

    def __init__(self, codeql_path: str = "codeql", debug: bool = False) -> None:
        self._codeql = codeql_path
        self._debug = debug

    def extract(self, target: Path) -> ExtractionResult:
        target = Path(target).resolve()
        self._ensure_packs()

        with tempfile.TemporaryDirectory(prefix="confusion_codeql_") as tmpdir:
            db_path = Path(tmpdir) / "db"
            self._create_database(target, db_path)

            routes = self._query_routes(db_path, target)
            accesses = self._query_accesses(db_path, target)
            edges = self._query_call_edges(db_path, target)

        # Build initial result from CodeQL, then augment with AST analysis
        # to fill gaps (aliased accesses, before_requests, dict_merges, etc.)
        codeql_result = ExtractionResult(
            routes=routes,
            input_accesses=accesses,
            call_edges=edges,
            before_requests=[],
            dict_merges=[],
        )
        return augment_with_ast(codeql_result, target)

    def _ensure_packs(self) -> None:
        """Auto-download CodeQL Python query pack and install query dependencies."""
        lock_file = _QUERIES_DIR / "codeql-pack.lock.yml"
        if lock_file.exists():
            return

        if self._debug:
            print("[codeql] Installing query pack dependencies...", file=sys.stderr)

        # Download the standard library pack
        subprocess.run(
            [self._codeql, "pack", "download", "codeql/python-all"],
            capture_output=not self._debug,
        )

        # Install dependencies for our query pack (creates lock file)
        subprocess.run(
            [self._codeql, "pack", "install"],
            cwd=str(_QUERIES_DIR),
            capture_output=not self._debug,
            check=True,
        )

    def _create_database(self, target: Path, db_path: Path) -> None:
        """Create a CodeQL database from the target Python source."""
        if self._debug:
            print(f"[codeql] Creating database at {db_path} from {target}", file=sys.stderr)

        cmd = [
            self._codeql, "database", "create",
            str(db_path),
            "--language=python",
            f"--source-root={target}",
            "--overwrite",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if self._debug and result.stderr:
            print(f"[codeql] DB creation stderr:\n{result.stderr[:500]}", file=sys.stderr)

        if result.returncode != 0:
            raise RuntimeError(f"codeql database create failed:\n{result.stderr}")

    def _run_query(self, db_path: Path, query_name: str) -> list[list[str]]:
        """Run a CodeQL query and return CSV-parsed results."""
        query_path = _QUERIES_DIR / f"{query_name}.ql"
        if not query_path.exists():
            raise FileNotFoundError(f"Query file not found: {query_path}")

        with tempfile.NamedTemporaryFile(suffix=".bqrs", delete=False) as bqrs_file:
            bqrs_path = bqrs_file.name

        try:
            # Run query
            run_result = subprocess.run(
                [
                    self._codeql, "query", "run",
                    str(query_path),
                    "--database", str(db_path),
                    "--output", bqrs_path,
                    "--search-path", str(_QUERIES_DIR),
                ],
                capture_output=True, text=True,
            )

            if self._debug and run_result.stderr:
                print(f"[codeql] Query {query_name} stderr:\n{run_result.stderr[:300]}", file=sys.stderr)

            if run_result.returncode != 0:
                if self._debug:
                    print(f"[codeql] Query {query_name} failed:\n{run_result.stderr}", file=sys.stderr)
                return []

            # Decode BQRS to CSV
            decode_result = subprocess.run(
                [
                    self._codeql, "bqrs", "decode",
                    bqrs_path,
                    "--format=csv",
                    "--no-titles",
                ],
                capture_output=True, text=True,
            )

            if decode_result.returncode != 0:
                if self._debug:
                    print(f"[codeql] BQRS decode failed:\n{decode_result.stderr}", file=sys.stderr)
                return []

            rows = list(csv.reader(io.StringIO(decode_result.stdout)))

            if self._debug:
                print(f"[codeql] Query {query_name}: {len(rows)} results", file=sys.stderr)

            return rows

        finally:
            os.unlink(bqrs_path)

    def _query_routes(self, db_path: Path, target: Path) -> list[RouteFact]:
        rows = self._run_query(db_path, "routes")

        # Group rows by handler identity (name, qualname, file, line, url)
        # because each HTTP method produces a separate row.
        grouped: OrderedDict[tuple[str, str, str, str, str], set[str]] = OrderedDict()
        for row in rows:
            if len(row) < 7:
                continue
            _handler_obj, name, qualname, file, line, url, method = row[:7]
            key = (name, qualname, file, line, url)
            grouped.setdefault(key, set())
            if method:
                grouped[key].add(method.upper())

        results = []
        for (name, qualname, file, line, url), methods in grouped.items():
            fq = _fix_qualname(name, qualname, file)
            results.append(RouteFact(
                handler_name=name,
                handler_qualname=fq,
                route_kind=RouteKind.DECORATOR,
                rule=url if url else None,
                methods=tuple(sorted(methods)) if methods else ("GET",),
                blueprint=None,
                location=Location(str(target / file) if file else "", int(line) if line else 0),
                raw_code="",
            ))
        return results

    def _query_accesses(self, db_path: Path, target: Path) -> list[InputAccessFact]:
        rows = self._run_query(db_path, "accesses")
        results = []
        for row in rows:
            if len(row) < 7:
                continue
            access_obj, source_name, accessor_name, key, func_qualname, file, line = row[:7]
            source = _SOURCE_MAP.get(source_name)
            if source is None:
                continue
            accessor = _ACCESSOR_MAP.get(accessor_name, AccessorKind.DIRECT)
            key_literal = key if key and key != "?" else None
            fq = _fix_qualname("", func_qualname, file)
            results.append(InputAccessFact(
                function_qualname=fq,
                location=Location(str(target / file) if file else "", int(line) if line else 0),
                source=source,
                accessor=accessor,
                key_expr=key if key != "?" else None,
                key_literal=key_literal,
                raw_code=access_obj or "",
            ))
        return results

    def _query_call_edges(self, db_path: Path, target: Path) -> list[CallEdge]:
        rows = self._run_query(db_path, "calledges")
        results = []
        for row in rows:
            if len(row) < 4:
                continue
            caller, callee_expr, file, line = row[:4]
            caller_fq = _fix_qualname("", caller, file)
            results.append(CallEdge(
                caller_qualname=caller_fq,
                callee_qualname=callee_expr,
                location=Location(str(target / file) if file else "", int(line) if line else 0),
            ))
        return results
