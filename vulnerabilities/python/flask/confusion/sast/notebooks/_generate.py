#!/usr/bin/env python3
"""Generate demonstration Jupyter notebooks for confusion SAST.

Run:
    cd sast/
    .venv/bin/python notebooks/_generate.py
"""

from pathlib import Path

import nbformat

NOTEBOOKS_DIR = Path(__file__).resolve().parent


def md(text: str):
    """Create a markdown cell (dedented)."""
    import textwrap
    return nbformat.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text: str):
    """Create a code cell (dedented)."""
    import textwrap
    return nbformat.v4.new_code_cell(textwrap.dedent(text).strip())


def new_notebook() -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    return nb


# ---------------------------------------------------------------------------
# Notebook 1: Quickstart
# ---------------------------------------------------------------------------


def generate_quickstart() -> nbformat.NotebookNode:
    nb = new_notebook()
    c = nb.cells

    c.append(md("""
        # Confusion SAST: Interactive Explorer

        This notebook walks through the core workflow: discovering targets,
        extracting analysis graphs, scanning for vulnerabilities, and exploring
        results interactively.
    """))

    c.append(code("""\
        %load_ext autoreload
        %autoreload 2
        from pathlib import Path
        from confusion_sast.notebook import *"""))

    c.append(code("""\
        t = targets()
        target = t.r01.e03"""))

    # --- Target selection ---

    c.append(md("""
        ## Target Selection

        The `targets()` registry auto-discovers exercises from the `webapp/` directory.
        Each section contains progressive exercises, from baseline to fixed.
    """))

    c.append(code("""\
        t"""))

    c.append(code("""\
        # Section and exercise objects are richer than raw Paths.
        print(t.r01)
        print(t.r01.e01)
        print(type(t.r01.e01).__name__, "->", Path(t.r01.e01))
        print(type(t.r01.e01.path).__name__, "->", t.r01.e01.path)
        print("batch_load(t.r01) loads one section; batch_load(t) loads everything")"""))

    # --- Loading a graph ---

    c.append(md("""
        ## Loading a Graph

        `load()` runs the AST backend to extract facts (routes, input accesses,
        call edges) and builds a queryable `AnalysisGraph`. Results are cached.
    """))

    c.append(code("""\
        g = load(target)
        g"""))

    c.append(code("""\
        # Notebook outputs are richer when you return objects directly.
        g.stats()"""))

    c.append(code("""\
        g.by_key()"""))

    c.append(md("""
        The graph object itself now renders as the interactive workbench,
        even before any findings exist. Use this for open-ended exploration
        of routes, call paths, and backend-extracted facts.
    """))

    c.append(code("""\
        Explorer(g)"""))

    # --- Scanning ---

    c.append(md("""
        ## Scanning for Vulnerabilities

        `scan()` extracts the graph and runs all detection rules. The result
        contains both `findings` and the underlying `graph`.
    """))

    c.append(code("""\
        r = scan(target)
        r"""))

    c.append(code("""\
        show(r.findings[0])"""))

    c.append(md("""
        `show(...)` is the notebook-oriented formatter. `print(...)` uses the
        plain string representation of the underlying Python object.
    """))

    c.append(code("""\
        print(r.findings[0])
        show(r.findings[0])
        r.findings[0]"""))

    # --- Interactive exploration ---

    c.append(md("""
        ## Interactive Exploration

        The `Explorer` widget is the main workbench. It accepts a graph,
        a scan result, or a graph plus explicit findings.
    """))

    c.append(code("""\
        Explorer(g)"""))

    c.append(code("""\
        Explorer(r)"""))

    # --- Query helpers ---

    c.append(md("""
        ## Querying the Graph

        Helper functions let you filter and explore the extracted data
        without manually iterating.
    """))

    c.append(code("""\
        # All form-source accesses
        accesses(g, source="form")"""))

    c.append(code("""\
        # Keys with divergent access patterns (different sources or accessors)
        diff_keys(g)"""))

    c.append(code("""\
        # Detailed view of a specific endpoint
        endpoint_detail("create_new_order", g)"""))

    # --- Multi-exercise scanning ---

    c.append(md("""
        ## Multi-Exercise Scanning

        Scan across an entire section to see how vulnerabilities evolve
        from baseline through exploitation to the fixed version.
    """))

    c.append(code("""\
        # Load all r01 exercises at once
        graphs = batch_load(t.r01)
        print(f"Loaded {len(graphs)} exercises")

        # Run all rules across all exercises
        from confusion_sast.detection.rules import run_all_rules
        results = BatchResult({name: run_all_rules(g) for name, g in graphs.items()})
        results"""))

    c.append(code("""\
        # Browse batch results exercise-by-exercise with the same workbench UX
        BatchExplorer(graphs, results)"""))

    # --- Individual widgets ---

    c.append(md("""
        ## Individual Widgets

        Use these when you want one part of the workbench in isolation.
    """))

    c.append(code("""\
        # Code viewer: show the source location of a finding
        viewer = CodeViewer()
        viewer.show_finding(r.findings[0])"""))

    c.append(code("""\
        # Code path view: inspect the route-to-evidence context
        cp = CodePathView(target_path=target.path)
        cp.show_finding(g, r.findings[0])
        cp.widget"""))

    c.append(code("""\
        # Graph view: focus the graph on a specific finding
        gv = GraphView(g, layout="dagre")
        gv.focus_finding(r.findings[0])
        gv.widget"""))

    c.append(code("""\
        # Endpoint browser: open-ended graph exploration
        et = EndpointTable(g)
        et.widget"""))

    return nb


# ---------------------------------------------------------------------------
# Notebook 2: Graph Exploration
# ---------------------------------------------------------------------------


def generate_graph_exploration() -> nbformat.NotebookNode:
    nb = new_notebook()
    c = nb.cells

    c.append(md("""
        # Graph Exploration

        Deep dive into the `AnalysisGraph` structure: nodes, edges,
        reachability, and call paths. We use `r01/e03` (order overwrite)
        which has multiple routes and a richer call graph.
    """))

    c.append(code("""\
        %load_ext autoreload
        %autoreload 2
        from confusion_sast.notebook import *"""))

    # --- Load and inspect ---

    c.append(md("""
        ## Graph Structure
    """))

    c.append(code("""\
        t = targets()
        g = load(t.r01.e03)
        g"""))

    c.append(code("""\
        g.stats()"""))

    # --- Raw nodes and edges ---

    c.append(md("""
        ## Raw NetworkX Data

        Under the hood, `g.g` is a `networkx.DiGraph`. Nodes are function
        qualnames; edges represent call relationships.
    """))

    c.append(code("""\
        # First 8 nodes with their attributes
        list(g.g.nodes(data=True))[:8]"""))

    c.append(code("""\
        # First 8 edges
        list(g.g.edges(data=True))[:8]"""))

    # --- Graph widget ---

    c.append(md("""
        ## Visual Graph

        `GraphView` renders the call graph as a focused navigation surface.
        It supports scope switching, text search, layout changes, and
        call-site inspection through clickable edges.
    """))

    c.append(code("""\
        gv = GraphView(g, layout="dagre")
        gv.widget"""))

    c.append(code("""\
        # Focus on a single endpoint and its reachable subgraph
        gv.focus_endpoint("routes.checkout_cart")
        gv.widget"""))

    c.append(code("""\
        # Endpoint browser for open-ended exploration
        et = EndpointTable(g)
        et.widget"""))

    c.append(code("""\
        # Code-path browser for source-grounded graph review
        cp = CodePathView(target_path=t.r01.e03.path)
        cp.show_function(g, "routes.checkout_cart")
        cp.widget"""))

    # --- Call paths ---

    c.append(md("""
        ## Call Paths

        Trace how a handler reaches a function that accesses user input.
    """))

    c.append(code("""\
        # What functions can create_new_order reach?
        reachable = g.reachable_from("routes.create_new_order")
        print(f"{len(reachable)} functions reachable")
        # Show the ones that have input accesses
        for fn in sorted(reachable):
            accs = g.accesses_in(fn)
            if accs:
                print(f"  {fn}: {[a.raw_code for a in accs]}")"""))

    c.append(code("""\
        # Shortest call path from handler to a callee
        path = g.call_path("routes.create_new_order", "utils.check_price_and_availability")
        print("Path:", path)

        path2 = g.call_path("routes.create_new_order", "utils.get_order_items")
        print("Path:", path2)"""))

    c.append(code("""\
        # Highlight a path in the graph view
        gv.reset_highlights()
        if path:
            gv.highlight_path(path)
        gv.widget"""))

    # --- Per-endpoint accesses ---

    c.append(md("""
        ## Input Accesses per Endpoint

        Each endpoint handler can reach input accesses in its own body
        and in any functions it calls.
    """))

    c.append(code("""\
        for handler, route, accs in g.by_endpoint():
            if not accs:
                continue
            sources = {a.source for a in accs}
            keys = {a.key_literal for a in accs if a.key_literal}
            print(f"{route.handler_name} ({route.rule} {route.methods})")
            print(f"  sources: {sources}")
            print(f"  keys: {keys}")
            print(f"  accesses: {len(accs)}")
            print()"""))

    # --- Source code ---

    c.append(md("""
        ## Source Code Context

        `show_source()` prints the source lines around an input access.
    """))

    c.append(code("""\
        # Show source for each form access
        form_accs = accesses(g, source="form")
        for a in form_accs[:3]:
            print(f"--- {a.function_qualname}: {a.raw_code} ---")
            show_source(a)
            print()"""))

    # --- NetworkX analysis ---

    c.append(md("""
        ## NetworkX Analysis

        Since the graph is a standard `networkx.DiGraph`, you can use
        any NetworkX algorithm.
    """))

    c.append(code("""\
        import networkx as nx

        # Weakly connected components
        components = list(nx.weakly_connected_components(g.g))
        print(f"{len(components)} weakly connected components")
        for i, comp in enumerate(sorted(components, key=len, reverse=True)[:3]):
            print(f"  Component {i}: {len(comp)} nodes")

        print()

        # Top nodes by out-degree (most callees)
        by_degree = sorted(g.g.out_degree(), key=lambda x: x[1], reverse=True)[:5]
        print("Top 5 by out-degree:")
        for node, deg in by_degree:
            print(f"  {node}: {deg}")"""))

    # --- Compare two exercises ---

    c.append(md("""
        ## Comparing Exercises

        Load two exercises side by side to see how the graph grows
        as vulnerabilities are introduced.
    """))

    c.append(code("""\
        g_e01 = load(t.r01.e01)
        g_e03 = load(t.r01.e03)

        stats_e01 = g_e01.stats()
        stats_e03 = g_e03.stats()

        print(f"{'Metric':<20} {'e01':>8} {'e03':>8} {'delta':>8}")
        print("-" * 48)
        for key in stats_e01:
            v1 = stats_e01[key]
            v3 = stats_e03[key]
            delta = v3 - v1
            sign = "+" if delta > 0 else ""
            print(f"{key:<20} {v1:>8} {v3:>8} {sign}{delta:>7}")

        print()
        print("e01 endpoints:", [r.handler_name for r in g_e01.routes])
        print("e03 endpoints:", [r.handler_name for r in g_e03.routes])
        print("New in e03:", set(r.handler_name for r in g_e03.routes) - set(r.handler_name for r in g_e01.routes))"""))

    return nb


# ---------------------------------------------------------------------------
# Notebook 3: Rule Development
# ---------------------------------------------------------------------------


def generate_rule_development() -> nbformat.NotebookNode:
    nb = new_notebook()
    c = nb.cells

    c.append(md("""
        # Rule Development

        Write, test, and iterate on detection rules interactively.
        Rules inspect the `AnalysisGraph` and yield `Finding` objects
        for each vulnerability pattern they detect.
    """))

    c.append(code("""\
        %load_ext autoreload
        %autoreload 2
        from confusion_sast.notebook import *"""))

    # --- Setup ---

    c.append(md("""
        ## Setup: Load a Known-Vulnerable Exercise

        `r01/e03` (order overwrite) has multiple vulnerability patterns:
        mixed JSON/form sources, dict merge overwrites, and conditional
        source selection.
    """))

    c.append(code("""\
        t = targets()
        g = load(t.r01.e03)
        g"""))

    # --- Existing rules ---

    c.append(md("""
        ## Existing Rules

        The rule registry tracks all built-in detection rules.
    """))

    c.append(code("""\
        from confusion_sast.detection.rules import get_all_rules

        rules = get_all_rules()
        for rule_id, fn in rules.items():
            print(f"{rule_id}: {fn.__name__}")"""))

    # --- Run specific rules ---

    c.append(md("""
        ## Running Specific Rules
    """))

    c.append(code("""\
        # Run a single rule by ID
        results = run_rule("CONF-005", g)
        print(f"CONF-005 found {len(results)} finding(s)")
        for f in results:
            show(f)"""))

    c.append(code("""\
        # Review those matches in the workbench
        Explorer(g, results, target_path=t.r01.e03.path)"""))

    c.append(code("""\
        results = run_rule("CONF-007", g)
        print(f"CONF-007 found {len(results)} finding(s)")
        for f in results:
            show(f)"""))

    # --- Simple ad-hoc rule ---

    c.append(md("""
        ## Writing an Ad-Hoc Rule

        The `@detect` decorator and `finding()` builder reduce boilerplate.
        A rule function receives an `AnalysisGraph` and yields findings.
    """))

    c.append(code("""\
        @detect("MY-001", severity="high")
        def mixed_json_form(g):
            \"\"\"Flag endpoints that read from both JSON and form sources.\"\"\"
            for handler, route, accs in g.by_endpoint():
                json_accs = [a for a in accs if a.source == InputSource.JSON]
                form_accs = [a for a in accs if a.source == InputSource.FORM]
                if json_accs and form_accs:
                    yield finding(
                        f"Endpoint uses both JSON and form: {route.handler_name}",
                        evidence=json_accs + form_accs,
                        endpoint=route,
                    )

        results = run_fn(mixed_json_form, g)
        show(results)"""))

    # --- More complex rule ---

    c.append(md("""
        ## A More Complex Rule

        This rule looks for endpoints where `request.form` is passed directly
        (as a dict-like object) rather than accessed by key -- a pattern that
        can smuggle unexpected fields.
    """))

    c.append(code("""\
        @detect("MY-002", severity="medium")
        def direct_source_passthrough(g):
            \"\"\"Flag direct passthrough of request source objects.\"\"\"
            for handler, route, accs in g.by_endpoint():
                direct = [a for a in accs if a.accessor == AccessorKind.DIRECT]
                if direct:
                    yield finding(
                        f"Direct source passthrough in {route.handler_name}: "
                        + ", ".join(a.source.value for a in direct),
                        evidence=direct,
                        endpoint=route,
                    )

        results = run_fn(direct_source_passthrough, g)
        show(results)"""))

    # --- Batch rule testing ---

    c.append(md("""
        ## Batch Rule Testing

        Instead of manually looping over exercises, use `batch_load()` to grab
        all graphs in a section and `batch_run()` to execute a rule against them.
        The resulting `BatchResult` renders as a summary table in Jupyter and
        offers drill-down helpers.
    """))

    c.append(code("""\
        graphs = batch_load(t.r01)
        graphs"""))

    c.append(code("""\
        # Run the ad-hoc rule across all r01 exercises
        results = batch_run(mixed_json_form, graphs)
        results"""))

    c.append(code("""\
        # Which exercises actually triggered findings?
        results.hits"""))

    c.append(code("""\
        # Drill into a specific exercise's findings
        for name in results.hits:
            print(f"--- {name} ---")
            for f in results[name]:
                show(f)"""))

    # --- Progressive rule refinement ---

    c.append(md("""
        ## Progressive Rule Refinement

        The batch workflow makes it easy to iterate on a rule: write a first
        draft, test it across exercises, tighten the logic, and verify the
        change in detection coverage.
    """))

    c.append(code("""\
        # Draft: flag ANY endpoint that accesses more than one input source
        @detect("DRAFT-001", severity="medium")
        def multi_source_naive(g):
            \"\"\"Flag endpoints reading from multiple input sources (broad).\"\"\"
            for handler, route, accs in g.by_endpoint():
                sources = {a.source for a in accs}
                if len(sources) > 1:
                    yield finding(
                        f"Multiple sources in {route.handler_name}: {sorted(s.value for s in sources)}",
                        evidence=accs,
                        endpoint=route,
                    )

        draft_results = batch_run(multi_source_naive, graphs)
        print(f"Draft rule: {draft_results.total} findings across {len(draft_results.hits)} exercises")
        draft_results"""))

    c.append(code("""\
        # Refined: only flag when the SAME key is read from different sources
        @detect("DRAFT-002", severity="high")
        def multi_source_same_key(g):
            \"\"\"Flag endpoints where the same key is read from different sources.\"\"\"
            for handler, route, accs in g.by_endpoint():
                key_sources: dict[str, set] = {}
                for a in accs:
                    if a.key_literal:
                        key_sources.setdefault(a.key_literal, set()).add(a.source)
                confused = {k: srcs for k, srcs in key_sources.items() if len(srcs) > 1}
                if confused:
                    evidence = [a for a in accs if a.key_literal in confused]
                    keys_str = ", ".join(sorted(confused))
                    yield finding(
                        f"Key confusion in {route.handler_name}: {keys_str}",
                        evidence=evidence,
                        endpoint=route,
                    )

        refined_results = batch_run(multi_source_same_key, graphs)
        print(f"Refined rule: {refined_results.total} findings across {len(refined_results.hits)} exercises")
        print(f"Reduction: {draft_results.total} -> {refined_results.total} findings")
        refined_results"""))

    c.append(code("""\
        # Inspect the refined rule directly in the workbench
        Explorer(g, run_fn(multi_source_same_key, g), target_path=t.r01.e03.path)"""))

    # --- Finding paths ---

    c.append(md("""
        ## Tracing Evidence

        `finding_paths()` shows the call chain from an endpoint handler
        to each piece of evidence.
    """))

    c.append(code("""\
        r = scan(t.r01.e03)
        for f in r.findings:
            print(f"\\n{f.rule_id}: {f.title}")
            paths = finding_paths(f, g)
            for ev, path in zip(f.evidence, paths):
                label = getattr(ev, "raw_code", str(ev))[:60]
                print(f"  {label}")
                print(f"    path: {path}")"""))

    # --- Show source for evidence ---

    c.append(md("""
        ## Evidence Source Code

        Inspect the actual source lines for each piece of evidence.
    """))

    c.append(code("""\
        # Show source context for all evidence in the first finding
        f0 = r.findings[0]
        print(f"Finding: {f0.title}\\n")
        for ev in f0.evidence:
            if hasattr(ev, "location"):
                show_source(ev)
                print()"""))

    # --- Register a rule ---

    c.append(md("""
        ## Registering a Rule

        Pass `register=True` to add your rule to the global registry.
        It will then run alongside built-in rules when you call `scan()`.
    """))

    c.append(code("""\
        @detect("MY-003", severity="high", register=True)
        def missing_key_validation(g):
            \"\"\"Flag endpoints with direct source access but no key-level gets.

            If a handler passes request.form directly to a function without
            first validating individual keys, arbitrary fields can leak through.
            \"\"\"
            for handler, route, accs in g.by_endpoint():
                direct = [a for a in accs if a.accessor == AccessorKind.DIRECT]
                keyed = [a for a in accs if a.key_literal is not None]
                if direct and not keyed:
                    yield finding(
                        f"No key validation in {route.handler_name}",
                        evidence=direct,
                        endpoint=route,
                    )

        # Now scan() includes MY-003 automatically
        r = scan(t.r01.e03)
        print("All findings (including MY-003):")
        for f in r.findings:
            print(f"  {f.rule_id}: {f.title}")"""))

    return nb


# ---------------------------------------------------------------------------
# Notebook 4: Graph Construction Demo
# ---------------------------------------------------------------------------


def generate_graph_construction_demo() -> nbformat.NotebookNode:
    nb = new_notebook()
    c = nb.cells

    c.append(md("""
        # Graph Construction Demo

        This notebook is a compact presentation demo for the custom graph-based
        SAST engine. It uses a deliberately tiny Flask snippet so the extracted
        facts and graph edges are easy to explain.
    """))

    c.append(md("""
        ## Demo Goal

        We want to show how source code becomes:

        1. backend-specific extraction output,
        2. normalized facts,
        3. an endpoint-centered `AnalysisGraph`,
        4. queryable evidence for later detection rules.

        The detection rules themselves are only shown briefly at the end.
    """))

    c.append(code("""\
        %load_ext autoreload
        %autoreload 2

        from __future__ import annotations

        import html
        import sys
        import tempfile
        import textwrap
        from pathlib import Path
        from IPython.display import HTML, Markdown, display

        # Make the notebook runnable from a fresh repo checkout even if the
        # package has not been installed with `pip install -e .`.
        for candidate in [Path.cwd(), *Path.cwd().parents]:
            if (candidate / "src" / "confusion_sast").exists():
                sys.path.insert(0, str(candidate / "src"))
                break

        from confusion_sast.analysis.graph import build_analysis_graph
        from confusion_sast.backends.ast_backend import ASTBackend
        from confusion_sast.detection.rules import run_rules
        from confusion_sast.reporting.display import show_graph


        def show_table(rows: list[dict], *, title: str | None = None) -> None:
            \"\"\"Small dependency-free table renderer for presentation notebooks.\"\"\"
            if title:
                display(Markdown(f\"**{title}**\"))
            if not rows:
                display(Markdown(\"_No rows._\"))
                return

            columns = list(rows[0].keys())
            header = \"\".join(f\"<th>{html.escape(str(col))}</th>\" for col in columns)
            body_rows = []
            for row in rows:
                cells = \"\".join(
                    f\"<td><code>{html.escape(str(row.get(col, '')))}</code></td>\"
                    for col in columns
                )
                body_rows.append(f\"<tr>{cells}</tr>\")
            display(HTML(f\"\"\"
            <style>
              table.demo-table {{
                border-collapse: collapse;
                font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 13px;
              }}
              .demo-table th, .demo-table td {{
                border: 1px solid #ddd;
                padding: 6px 8px;
                vertical-align: top;
              }}
              .demo-table th {{
                background: #f6f6f6;
                text-align: left;
              }}
            </style>
            <table class=\"demo-table\">
              <thead><tr>{header}</tr></thead>
              <tbody>{''.join(body_rows)}</tbody>
            </table>
            \"\"\"))"""))

    c.append(md("""
        ## 1. Tiny Flask Program

        This toy endpoint contains the same structural idea as the delivery-fee
        benchmark: the order path uses `request.form`, while the delivery-fee
        path uses `request.values`. Both paths call the same helper.
    """))

    c.append(code("""\
        demo_source = '''
        from flask import Blueprint, jsonify, request

        bp = Blueprint("demo", __name__)


        def check_items(data):
            return data.getlist("items")


        def calculate_delivery_fee():
            items_for_fee = check_items(request.values)
            return 0 if len(items_for_fee) > 2 else 5


        @bp.before_request
        def reject_negative_tip():
            tip = request.args.get("tip")
            if tip and tip.startswith("-"):
                return jsonify({"error": "negative tip"}), 400


        @bp.post("/orders")
        def create_order():
            checked_items = check_items(request.form)
            if not checked_items:
                return jsonify({"error": "empty order"}), 400

            delivery_fee = calculate_delivery_fee()
            ordered_items = check_items(request.form)
            return jsonify({"items": ordered_items, "delivery_fee": delivery_fee})
        '''

        demo_dir = Path(tempfile.mkdtemp(prefix="confusion_graph_demo_"))
        demo_file = demo_dir / "app.py"
        demo_file.write_text(textwrap.dedent(demo_source).strip() + "\\n", encoding="utf-8")

        print(f"Demo source written to: {demo_file}\\n")
        for i, line in enumerate(demo_file.read_text().splitlines(), start=1):
            print(f"{i:>2}: {line}")"""))

    c.append(md("""
        ## 2. Extraction Backend

        The AST backend walks Python syntax and extracts framework-aware facts:
        routes, request input accesses, call edges, and middleware registrations.

        At this stage we still do not have the final analysis graph. We only
        have normalized facts produced by one backend.
    """))

    c.append(code("""\
        backend = ASTBackend()
        extraction = backend.extract(demo_dir)

        print("Extraction counts")
        print(f"  routes:          {len(extraction.routes)}")
        print(f"  input accesses:  {len(extraction.input_accesses)}")
        print(f"  call edges:      {len(extraction.call_edges)}")
        print(f"  before_request:  {len(extraction.before_requests)}")
        print(f"  dict merges:     {len(extraction.dict_merges)}")"""))

    c.append(md("""
        ## 3. Normalized Facts

        These fact objects are the contract between backends and rules. A rule
        does not need to know whether a fact came from AST, CodeQL, Joern, or a
        combined backend.
    """))

    c.append(code("""\
        show_table(
            [
                {
                    "handler": r.handler_qualname,
                    "methods": ",".join(r.methods),
                    "rule": r.rule,
                    "blueprint": r.blueprint,
                    "line": r.location.line,
                }
                for r in extraction.routes
            ],
            title="RouteFact",
        )

        show_table(
            [
                {
                    "function": a.function_qualname,
                    "source": f"request.{a.source.value}",
                    "accessor": a.accessor.value,
                    "key": a.key_literal,
                    "line": a.location.line,
                    "notes": "; ".join(a.notes),
                }
                for a in extraction.input_accesses
            ],
            title="InputAccessFact",
        )"""))

    c.append(code("""\
        show_table(
            [
                {
                    "caller": e.caller_qualname,
                    "callee": e.callee_qualname,
                    "line": e.location.line,
                    "argument_map": e.argument_map,
                }
                for e in extraction.call_edges
            ],
            title="CallEdge",
        )

        show_table(
            [
                {
                    "function": b.function_qualname,
                    "blueprint": b.blueprint,
                    "line": b.location.line,
                }
                for b in extraction.before_requests
            ],
            title="BeforeRequestFact",
        )"""))

    c.append(md("""
        Notice the `argument_map` on call edges. It records facts such as:

        ```text
        create_order -> check_items       {0: "request.form"}
        calculate_delivery_fee -> check_items {0: "request.values"}
        ```

        That is the information a syntax-only rule cannot reliably preserve
        once request data is passed into helper functions.
    """))

    c.append(md("""
        ## 4. Build the AnalysisGraph

        The `AnalysisGraph` adds a NetworkX call graph on top of the facts and
        builds indexes for common rule queries.

        - nodes are function qualified names,
        - edges are caller/callee relationships,
        - fact lists remain attached as queryable metadata.
    """))

    c.append(code("""\
        graph = build_analysis_graph(extraction, target_root=demo_dir)
        graph.stats()"""))

    c.append(code("""\
        # Visual graph view.
        #
        # In JupyterLab this renders the call graph as an HTML/SVG view.
        # For this demo:
        #   - green endpoint node: create_order
        #   - middleware node: reject_negative_tip
        #   - ordinary function nodes: helpers
        #   - directed edges: caller -> callee
        show_graph(graph)"""))

    c.append(code("""\
        show_table(
            [
                {
                    "node": node,
                    "kind": data.get("kind", "function"),
                }
                for node, data in sorted(graph.g.nodes(data=True))
            ],
            title="NetworkX nodes",
        )

        show_table(
            [
                {
                    "caller": caller,
                    "callee": callee,
                    "call_count": data.get("call_count"),
                }
                for caller, callee, data in sorted(graph.g.edges(data=True))
            ],
            title="NetworkX edges",
        )"""))

    c.append(md("""
        ## 5. Endpoint-Centered Queries

        Detection rules usually start from a route handler and ask:

        > Which functions and request accesses are reachable from this endpoint?

        This is why the graph is endpoint-centered rather than just a list of
        local source-code matches.
    """))

    c.append(code("""\
        route = extraction.routes[0]
        handler = route.handler_qualname

        print("Endpoint:", route.methods, route.rule)
        print("Handler: ", handler)
        print("\\nReachable functions:")
        for function_name in sorted(graph.reachable_from(handler)):
            print("  -", function_name)

        show_table(
            [
                {
                    "function": a.function_qualname,
                    "source": f"request.{a.source.value}",
                    "accessor": a.accessor.value,
                    "key": a.key_literal,
                    "line": a.location.line,
                    "notes": "; ".join(a.notes),
                }
                for a in graph.accesses_reachable_from(handler)
            ],
            title="Input accesses reachable from the /orders endpoint",
        )"""))

    c.append(md("""
        ## 6. Bridge to Detection Rules

        The detection rule can now compare endpoint-visible source policies:

        - `check_items(request.form)` for order validation/execution,
        - `check_items(request.values)` for delivery-fee calculation.

        This cell is only a bridge to the later detection-rules slide.
    """))

    c.append(code("""\
        findings = run_rules(graph, ["CONF-001"])
        print(f"CONF-001 findings: {len(findings)}\\n")

        for finding in findings:
            print(finding.title)
            print("primary location:", finding.location_1)
            print("related location:", finding.location_2)
            print("evidence:")
            for ev in finding.evidence:
                print(f"  - {ev.source.value}.{ev.accessor.value}({ev.key_literal!r}) at line {ev.location.line}")"""))

    c.append(md("""
        ## Presentation Summary

        The important point is not the specific rule result. The important
        point is the representation:

        ```text
        source code -> normalized facts -> call graph + indexes -> endpoint query
        ```

        Once this representation exists, detection rules can reason about
        semantic disagreement between code paths instead of matching only local
        syntax.
    """))

    return nb


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    notebooks = [
        ("01_quickstart.ipynb", generate_quickstart),
        ("02_graph_exploration.ipynb", generate_graph_exploration),
        ("03_rule_development.ipynb", generate_rule_development),
        ("04_graph_construction_demo.ipynb", generate_graph_construction_demo),
    ]

    for filename, generator in notebooks:
        nb = generator()
        path = NOTEBOOKS_DIR / filename
        nbformat.write(nb, str(path))
        print(f"Generated {path} ({len(nb.cells)} cells)")


if __name__ == "__main__":
    main()
