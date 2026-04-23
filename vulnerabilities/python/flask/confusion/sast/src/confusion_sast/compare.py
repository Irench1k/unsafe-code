"""Backend comparison and result serialization.

Provides tools for:
- Serializing/deserializing ExtractionResults to JSON
- Running multiple backends on the same target
- Comparing extraction results across backends
- Identifying gaps and mismatches

Usage (CLI):
    confusion-scan target/ --dump results.json
    confusion-scan target/ --dump results.json --backend joern

Usage (Python):
    from confusion_sast.compare import compare_backends, serialize_result, load_result

    results = compare_backends("path/to/app", ["ast", "joern", "codeql"])
    results.print_diff()
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from .analysis.graph import AnalysisGraph, build_analysis_graph
from .backends.interface import ExtractionResult
from .detection.rules import run_all_rules
from .models import (
    AccessorKind,
    BeforeRequestFact,
    CallEdge,
    DictMergeFact,
    Finding,
    InputAccessFact,
    InputSource,
    Location,
    RouteFact,
    RouteKind,
)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def serialize_result(result: ExtractionResult, backend_name: str = "unknown") -> dict:
    """Serialize an ExtractionResult to a JSON-compatible dict."""
    return {
        "backend": backend_name,
        "routes": [_serialize_route(r) for r in result.routes],
        "input_accesses": [_serialize_access(a) for a in result.input_accesses],
        "call_edges": [_serialize_edge(e) for e in result.call_edges],
        "before_requests": [_serialize_before(b) for b in result.before_requests],
        "dict_merges": [_serialize_merge(m) for m in result.dict_merges],
    }


def _serialize_route(r: RouteFact) -> dict:
    return {
        "handler_name": r.handler_name,
        "handler_qualname": r.handler_qualname,
        "route_kind": r.route_kind.value,
        "rule": r.rule,
        "methods": list(r.methods),
        "blueprint": r.blueprint,
        "location": {"file": r.location.file, "line": r.location.line},
        "raw_code": r.raw_code,
        "notes": list(r.notes),
    }


def _serialize_access(a: InputAccessFact) -> dict:
    return {
        "function_qualname": a.function_qualname,
        "source": a.source.value,
        "accessor": a.accessor.value,
        "key_literal": a.key_literal,
        "key_expr": a.key_expr,
        "location": {"file": a.location.file, "line": a.location.line},
        "raw_code": a.raw_code,
        "notes": list(a.notes),
    }


def _serialize_edge(e: CallEdge) -> dict:
    return {
        "caller": e.caller_qualname,
        "callee": e.callee_qualname,
        "location": {"file": e.location.file, "line": e.location.line},
    }


def _serialize_before(b: BeforeRequestFact) -> dict:
    return {
        "function_qualname": b.function_qualname,
        "blueprint": b.blueprint,
        "location": {"file": b.location.file, "line": b.location.line},
    }


def _serialize_merge(m: DictMergeFact) -> dict:
    return {
        "function_qualname": m.function_qualname,
        "sources": list(m.sources),
        "location": {"file": m.location.file, "line": m.location.line},
        "raw_code": m.raw_code,
    }


def dump_result(result: ExtractionResult, path: str | Path, backend_name: str = "unknown") -> None:
    """Serialize and write extraction results to a JSON file."""
    data = serialize_result(result, backend_name)
    Path(path).write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


class ComparisonResult:
    """Results of comparing multiple backends on the same target."""

    def __init__(self, target: Path, backend_results: dict[str, ExtractionResult]) -> None:
        self.target = target
        self.backend_results = backend_results
        self.graphs = {name: build_analysis_graph(r) for name, r in backend_results.items()}
        self.findings = {name: run_all_rules(g) for name, g in self.graphs.items()}

    def stats_table(self) -> list[dict]:
        """Return per-backend stats as a list of dicts."""
        rows = []
        for name, result in self.backend_results.items():
            graph = self.graphs[name]
            s = graph.stats()
            rows.append({
                "backend": name,
                "routes": len(result.routes),
                "accesses": len(result.input_accesses),
                "call_edges": len(result.call_edges),
                "before_reqs": len(result.before_requests),
                "dict_merges": len(result.dict_merges),
                "nodes": s["nodes"],
                "edges": s["edges"],
                "unique_keys": s["unique_keys"],
                "unique_sources": s["unique_sources"],
                "findings": len(self.findings[name]),
            })
        return rows

    def route_diff(self) -> dict:
        """Compare routes across backends."""
        all_routes: dict[str, dict[str, RouteFact | None]] = defaultdict(dict)
        for backend, result in self.backend_results.items():
            for r in result.routes:
                key = f"{','.join(r.methods)} {r.rule or '?'}"
                all_routes[key][backend] = r
        return dict(all_routes)

    def access_diff(self) -> dict:
        """Compare input accesses across backends."""
        all_accesses: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for backend, result in self.backend_results.items():
            for a in result.input_accesses:
                if a.accessor == AccessorKind.DIRECT:
                    key = a.source.value
                else:
                    key = f"{a.source.value}.{a.accessor.value}({a.key_literal or '?'})"
                all_accesses[key][backend].append(a)
        return dict(all_accesses)

    def finding_diff(self) -> dict:
        """Compare findings across backends."""
        all_findings: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        for backend, findings in self.findings.items():
            for f in findings:
                all_findings[f.rule_id][backend].append(f)
        return dict(all_findings)

    def print_summary(self) -> None:
        """Print a comparison summary to stdout."""
        # Stats table
        stats = self.stats_table()
        print(f"\n{'Backend':<10} {'Routes':>7} {'Access':>7} {'Edges':>7} {'Keys':>5} {'Src':>4} {'Findings':>8}")
        print("-" * 60)
        for s in stats:
            print(f"{s['backend']:<10} {s['routes']:>7} {s['accesses']:>7} {s['call_edges']:>7} "
                  f"{s['unique_keys']:>5} {s['unique_sources']:>4} {s['findings']:>8}")

        # Route coverage
        rdiff = self.route_diff()
        backends = list(self.backend_results.keys())
        print(f"\nRoute coverage ({len(rdiff)} unique routes):")
        for route_key, backend_map in sorted(rdiff.items()):
            present = [b for b in backends if b in backend_map]
            missing = [b for b in backends if b not in backend_map]
            if missing:
                print(f"  {route_key:40s}  present={','.join(present):15s}  MISSING={','.join(missing)}")

        # Access coverage
        adiff = self.access_diff()
        print(f"\nAccess coverage ({len(adiff)} unique access patterns):")
        for access_key, backend_map in sorted(adiff.items()):
            present = {b: len(v) for b, v in backend_map.items()}
            missing = [b for b in backends if b not in backend_map]
            if missing:
                present_str = ", ".join(f"{b}={n}" for b, n in present.items())
                print(f"  {access_key:40s}  [{present_str}]  MISSING={','.join(missing)}")

        # Finding coverage
        fdiff = self.finding_diff()
        print(f"\nFinding coverage ({len(fdiff)} rules fired):")
        for rule_id, backend_map in sorted(fdiff.items()):
            counts = {b: len(v) for b, v in backend_map.items()}
            missing = [b for b in backends if b not in backend_map]
            line = f"  {rule_id}: " + ", ".join(f"{b}={n}" for b, n in counts.items())
            if missing:
                line += f"  MISSING={','.join(missing)}"
            print(line)

    def dump(self, path: str | Path) -> None:
        """Dump full comparison data to JSON."""
        data = {
            "target": str(self.target),
            "backends": {},
        }
        for name, result in self.backend_results.items():
            data["backends"][name] = serialize_result(result, name)
        Path(path).write_text(json.dumps(data, indent=2))


def compare_backends(
    target: str | Path,
    backends: list[str] | None = None,
    debug: bool = False,
) -> ComparisonResult:
    """Run multiple backends on the same target and return comparison."""
    from .pipeline import _get_backend

    if backends is None:
        backends = ["ast"]
    target = Path(target).resolve()

    results = {}
    for name in backends:
        if debug:
            print(f"[compare] Running {name} backend...", file=sys.stderr)
        t0 = time.monotonic()
        try:
            backend = _get_backend(name)
            results[name] = backend.extract(target)
            elapsed = time.monotonic() - t0
            if debug:
                r = results[name]
                print(f"[compare] {name}: {len(r.routes)} routes, {len(r.input_accesses)} accesses, "
                      f"{len(r.call_edges)} edges in {elapsed:.1f}s", file=sys.stderr)
        except Exception as e:
            print(f"[compare] {name} FAILED: {e}", file=sys.stderr)

    return ComparisonResult(target, results)
