"""CLI entry point for confusion-scan."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .backends.ast_backend import ASTBackend
from .analysis.graph import build_analysis_graph
from .detection.rules import get_all_rules, run_rules
from .reporting.formatter import format_findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="confusion-scan",
        description="Scan Flask apps for confusion/inconsistent interpretation vulnerabilities",
    )
    parser.add_argument(
        "target",
        type=Path,
        nargs="?",
        help="Path to the Flask application directory or file to scan",
    )
    parser.add_argument(
        "--backend",
        choices=["ast", "joern", "codeql", "chimera"],
        default="ast",
        help="Code analysis backend to use (default: ast)",
    )
    parser.add_argument(
        "--rules",
        nargs="*",
        help="Specific rule IDs to run (default: all)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed evidence for each finding",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show graph stats, backend logs, and timing",
    )
    parser.add_argument(
        "--dump",
        type=Path,
        help="Dump extraction results to JSON file (for comparison/debugging)",
    )
    parser.add_argument(
        "--compare",
        nargs="*",
        metavar="BACKEND",
        help="Run multiple backends and compare results (e.g. --compare ast joern codeql)",
    )
    parser.add_argument(
        "--list-rules",
        action="store_true",
        help="List all available detection rules and exit",
    )

    args = parser.parse_args(argv)

    if args.list_rules:
        for rule_id, fn in sorted(get_all_rules().items()):
            print(f"  {rule_id}: {fn.__doc__ or 'No description'}")
        return 0

    if args.target is None:
        parser.error("the following arguments are required: target")

    debug = args.debug

    # Compare mode: run multiple backends and show diff
    if args.compare is not None:
        from .compare import compare_backends
        backends = args.compare if args.compare else ["ast", "joern", "codeql"]
        target = args.target.resolve()
        comp = compare_backends(target, backends, debug=True)
        comp.print_summary()
        if args.dump:
            comp.dump(args.dump)
            print(f"\nDumped to {args.dump}", file=sys.stderr)
        return 0

    if args.backend == "ast":
        backend = ASTBackend()
    elif args.backend == "joern":
        from .backends.joern_backend import JoernBackend
        backend = JoernBackend(debug=debug)
    elif args.backend == "codeql":
        from .backends.codeql_backend import CodeQLBackend
        backend = CodeQLBackend(debug=debug)
    elif args.backend == "chimera":
        from .backends.chimera_backend import ChimeraBackend
        backend = ChimeraBackend(debug=debug)
    else:
        print(f"Unknown backend: {args.backend}", file=sys.stderr)
        return 1

    target = args.target.resolve()
    if not target.exists():
        print(f"Target not found: {target}", file=sys.stderr)
        return 1

    # Extraction phase
    t0 = time.monotonic()
    result = backend.extract(target)
    t_extract = time.monotonic() - t0

    # Dump extraction results if requested
    if args.dump:
        from .compare import dump_result
        dump_result(result, args.dump, args.backend)
        if debug:
            print(f"[dump] Wrote extraction results to {args.dump}", file=sys.stderr)

    # Build graph
    t1 = time.monotonic()
    graph = build_analysis_graph(result)
    t_graph = time.monotonic() - t1

    # Run rules
    t2 = time.monotonic()
    findings = run_rules(graph, args.rules)
    t_rules = time.monotonic() - t2

    # Stats output (on -v or --debug)
    if args.verbose or debug:
        stats = graph.stats()
        print(
            f"[{args.backend}] {stats['routes']} routes, "
            f"{stats['input_accesses']} accesses, "
            f"{stats['nodes']} nodes, {stats['edges']} edges, "
            f"{stats['unique_keys']} keys, {stats['unique_sources']} sources",
            file=sys.stderr,
        )

    if debug:
        print(
            f"[timing] extract={t_extract:.2f}s graph={t_graph:.3f}s rules={t_rules:.3f}s",
            file=sys.stderr,
        )

    print(format_findings(findings, verbose=args.verbose))
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
