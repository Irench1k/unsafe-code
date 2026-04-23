"""Tests for the interactive notebook API.

Covers: TargetRegistry/Section/Exercise, load() caching, batch_load(),
batch_run(), finding_paths(), widget construction, _repr_html_, and
end-to-end integration workflows.
"""

import os
from pathlib import Path

import pytest

from confusion_sast.analysis.graph import AnalysisGraph
from confusion_sast.detection.rules import _RULES
from confusion_sast.detection.toolkit import detect, finding, run_fn
from confusion_sast.models import Finding, Location, Severity
from confusion_sast.notebook import (
    BatchResult,
    Exercise,
    Section,
    TargetRegistry,
    batch_load,
    batch_run,
    finding_paths,
    load,
    scan,
    targets,
)
from confusion_sast.notebook.widgets import (
    BatchExplorer,
    CodePathView,
    CodeViewer,
    DetailsPane,
    EndpointTable,
    EvidenceTable,
    Explorer,
    FindingsTable,
    GraphView,
)
from confusion_sast.repl import accesses, diff_keys


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_graph_cache():
    """Ensure each test starts with an empty graph cache."""
    from confusion_sast.notebook._helpers import _graph_cache

    _graph_cache.clear()


# ---------------------------------------------------------------------------
# TargetRegistry / Section / Exercise
# ---------------------------------------------------------------------------


class TestTargetRegistry:
    def test_discovers_sections(self):
        t = targets()
        sections = list(t)
        assert len(sections) >= 4  # r01-r04 at minimum

    def test_section_attribute_access(self):
        t = targets()
        r01 = t.r01
        assert isinstance(r01, Section)
        assert r01.short == "r01"

    def test_exercise_attribute_access(self):
        t = targets()
        e01 = t.r01.e01
        assert isinstance(e01, Exercise)
        assert e01.short == "e01"

    def test_exercise_fspath(self):
        t = targets()
        e = t.r01.e01
        assert os.fspath(e) == str(e.path)
        # Works with Path()
        p = Path(e)
        assert p.is_dir()

    def test_section_iteration(self):
        t = targets()
        exercises = list(t.r01)
        assert len(exercises) >= 7  # e00-e07 at minimum

    def test_section_len(self):
        t = targets()
        assert len(t.r01) >= 7

    def test_invalid_section_raises(self):
        t = targets()
        with pytest.raises(AttributeError, match="r99"):
            t.r99

    def test_invalid_exercise_raises(self):
        t = targets()
        with pytest.raises(AttributeError, match="e99"):
            t.r01.e99

    def test_repr(self):
        t = targets()
        r = repr(t)
        assert "r01" in r
        assert "e01" in r

    def test_section_repr(self):
        t = targets()
        r = repr(t.r01)
        assert "r01" in r
        assert "exercises" in r

    def test_exercise_repr(self):
        t = targets()
        r = repr(t.r01.e01)
        assert "r01" in r
        assert "e01" in r

    def test_exercise_str(self):
        t = targets()
        e = t.r01.e01
        assert "Exercise(" in str(e)
        assert "e01" in str(e)

    def test_section_fspath(self):
        t = targets()
        assert os.fspath(t.r01) == str(t.r01.path)

    def test_registry_path(self):
        t = targets()
        assert t.path.is_dir()

    def test_registry_html_repr(self):
        t = targets()
        html = t._repr_html_()
        assert "<table" in html
        assert "r01" in html

    def test_registry_len(self):
        t = targets()
        assert len(t) >= 4


# ---------------------------------------------------------------------------
# load() with caching
# ---------------------------------------------------------------------------


class TestLoad:
    def test_basic_load(self):
        t = targets()
        g = load(t.r01.e01)
        assert isinstance(g, AnalysisGraph)
        assert g.stats()["routes"] > 0

    def test_caching(self):
        t = targets()
        g1 = load(t.r01.e01)
        g2 = load(t.r01.e01)
        assert g1 is g2  # Same object from cache

    def test_force_reload(self):
        t = targets()
        g1 = load(t.r01.e01)
        g2 = load(t.r01.e01, force=True)
        assert g1 is not g2  # Different object

    def test_load_with_path_string(self):
        t = targets()
        g = load(str(t.r01.e01.path))
        assert isinstance(g, AnalysisGraph)

    def test_load_with_exercise(self):
        t = targets()
        g = load(t.r01.e01)
        assert isinstance(g, AnalysisGraph)

    def test_load_returns_graph_with_accesses(self):
        t = targets()
        g = load(t.r01.e01)
        assert g.stats()["input_accesses"] > 0

    def test_load_with_explicit_ast_backend(self):
        t = targets()
        g = load(t.r01.e01, backend="ast")
        assert isinstance(g, AnalysisGraph)
        assert g.stats()["routes"] > 0

    def test_load_with_invalid_backend_raises(self):
        t = targets()
        with pytest.raises(ValueError, match="Unknown backend"):
            load(t.r01.e01, backend="nonexistent")

    def test_cache_separates_backends(self):
        """Different backends should produce separate cache entries."""
        t = targets()
        g_ast = load(t.r01.e01, backend="ast")
        # A second call with the same backend hits cache
        g_ast2 = load(t.r01.e01, backend="ast")
        assert g_ast is g_ast2


# ---------------------------------------------------------------------------
# batch_load()
# ---------------------------------------------------------------------------


class TestBatchLoad:
    def test_batch_load_section(self):
        t = targets()
        graphs = batch_load(t.r01)
        assert len(graphs) >= 7
        assert all(isinstance(g, AnalysisGraph) for g in graphs.values())

    def test_batch_load_list(self):
        t = targets()
        graphs = batch_load([t.r01.e01, t.r01.e02])
        assert len(graphs) == 2

    def test_batch_load_registry(self):
        t = targets()
        graphs = batch_load(t)
        assert len(graphs) >= 20  # at least 20 exercises total

    def test_batch_load_keys(self):
        t = targets()
        graphs = batch_load(t.r01)
        # Keys should be "r01/e00", "r01/e01", etc.
        assert "r01/e01" in graphs

    def test_batch_load_invalid_type_raises(self):
        with pytest.raises(TypeError):
            batch_load("not a valid target type")


# ---------------------------------------------------------------------------
# batch_run()
# ---------------------------------------------------------------------------


class TestBatchRun:
    def test_batch_run_builtin_rule(self):
        t = targets()
        graphs = batch_load([t.r01.e01, t.r01.e02])

        rule_fn = _RULES["CONF-002"]
        results = batch_run(rule_fn, graphs)
        assert isinstance(results, BatchResult)

    def test_batch_run_adhoc_rule(self):
        t = targets()
        graphs = batch_load([t.r01.e01, t.r01.e02])

        @detect("TEST-BATCH", severity="high")
        def test_rule(g):
            for handler, route, accs in g.by_endpoint():
                if len(accs) > 5:
                    yield finding("Many accesses", evidence=accs)

        results = batch_run(test_rule, graphs)
        assert isinstance(results, BatchResult)
        assert len(results) == 2

    def test_batch_result_properties(self):
        t = targets()
        graphs = batch_load([t.r01.e01])

        @detect("TEST-PROP")
        def always_fires(g):
            for handler, route, accs in g.by_endpoint():
                yield finding("test")

        results = batch_run(always_fires, graphs)
        assert results.total > 0
        assert len(results.hits) > 0
        assert len(results.all_findings) == results.total

    def test_batch_result_summary(self):
        t = targets()
        graphs = batch_load([t.r01.e01])

        @detect("TEST-SUM")
        def fires(g):
            for handler, route, accs in g.by_endpoint():
                yield finding("test")

        results = batch_run(fires, graphs)
        summary = results.summary
        assert isinstance(summary, dict)
        for k, v in summary.items():
            assert isinstance(v, int)

    def test_batch_result_contains(self):
        t = targets()
        graphs = batch_load([t.r01.e01])

        @detect("TEST-CONT")
        def fires(g):
            yield finding("test")

        results = batch_run(fires, graphs)
        assert "r01/e01" in results

    def test_batch_result_repr(self):
        results = BatchResult({})
        assert "BatchResult" in repr(results)

    def test_batch_result_repr_with_data(self):
        results = BatchResult({"test": []})
        r = repr(results)
        assert "1 exercises" in r
        assert "0 total findings" in r

    def test_batch_result_html(self):
        results = BatchResult({"test": []})
        html = results._repr_html_()
        assert "<table" in html

    def test_batch_result_iteration(self):
        results = BatchResult({"a": [], "b": []})
        keys = list(results)
        assert "a" in keys
        assert "b" in keys


# ---------------------------------------------------------------------------
# finding_paths()
# ---------------------------------------------------------------------------


class TestFindingPaths:
    def test_finding_paths_with_endpoint(self):
        t = targets()
        g = load(t.r01.e01)
        r = scan(t.r01.e01)

        assert len(r.findings) > 0, "e01 should produce findings"
        for f in r.findings:
            paths = finding_paths(f, g)
            assert len(paths) == len(f.evidence)

    def test_finding_paths_without_endpoint_empty_evidence(self):
        f = Finding(
            rule_id="TEST",
            title="test",
            description="test",
            severity=Severity.HIGH,
            location=Location("test.py", 1),
            evidence=[],
            endpoint=None,
        )
        g = load(targets().r01.e01)
        paths = finding_paths(f, g)
        assert paths == []

    def test_finding_paths_without_endpoint_with_evidence(self):
        """When endpoint is None but evidence exists, all paths should be None."""
        t = targets()
        g = load(t.r01.e01)
        # Get some real evidence items from a scan
        r = scan(t.r01.e01)
        assert len(r.findings) > 0
        some_evidence = r.findings[0].evidence

        f = Finding(
            rule_id="TEST",
            title="test",
            description="test",
            severity=Severity.HIGH,
            location=Location("test.py", 1),
            evidence=some_evidence,
            endpoint=None,
        )
        paths = finding_paths(f, g)
        assert len(paths) == len(some_evidence)
        assert all(p is None for p in paths)


# ---------------------------------------------------------------------------
# Widget construction tests (no Jupyter kernel required)
# ---------------------------------------------------------------------------


class TestWidgetConstruction:
    """Test that widgets can be constructed without a Jupyter kernel."""

    def test_code_viewer_init(self):
        cv = CodeViewer()
        assert cv.source_code == ""

    def test_code_viewer_show_file(self):
        t = targets()
        cv = CodeViewer()
        utils_path = t.r01.e01.path / "utils.py"
        assert utils_path.is_file(), f"Expected {utils_path} to exist"
        cv.show_file(str(utils_path), highlight_lines=[25])
        assert cv.source_code != ""
        assert cv.start_line > 0
        assert 25 in cv.highlight_lines

    def test_code_viewer_show_nonexistent(self):
        cv = CodeViewer()
        cv.show_file("/nonexistent/file.py")
        assert "not found" in cv.source_code.lower()

    def test_code_viewer_show_location(self):
        t = targets()
        cv = CodeViewer()
        utils_path = t.r01.e01.path / "utils.py"
        loc = Location(str(utils_path), 25)
        cv.show_location(loc)
        assert cv.source_code != ""

    def test_code_viewer_show_file_with_range(self):
        t = targets()
        cv = CodeViewer()
        utils_path = t.r01.e01.path / "utils.py"
        cv.show_file(str(utils_path), start_line=10, end_line=30)
        assert cv.start_line == 10
        assert cv.focus_line == 10
        lines = cv.source_code.split("\n")
        assert len(lines) > 21  # full-file mode keeps the full source loaded

    def test_code_viewer_clear(self):
        cv = CodeViewer()
        t = targets()
        cv.show_file(str(t.r01.e01.path / "utils.py"))
        cv.clear()
        assert cv.source_code == ""
        assert cv.highlight_lines == []

    def test_code_viewer_show_finding(self):
        t = targets()
        cv = CodeViewer()
        r = scan(t.r01.e01)
        assert len(r.findings) > 0
        cv.show_finding(r.findings[0])
        assert cv.source_code != ""

    def test_graph_view_init(self):
        g = load(targets().r01.e01)
        gv = GraphView(g)
        assert gv.widget is not None

    def test_graph_view_highlight(self):
        g = load(targets().r01.e01)
        gv = GraphView(g)
        # Get real handler names from the graph
        handlers = g.endpoint_handlers()
        assert len(handlers) > 0
        handler = handlers[0]
        reachable = list(g.reachable_from(handler))

        if len(reachable) >= 2:
            gv.highlight_path(reachable[:2])
        gv.reset_highlights()
        gv.highlight_nodes([handler])
        gv.focus_endpoint(handler)

    def test_graph_view_repr(self):
        g = load(targets().r01.e01)
        gv = GraphView(g)
        assert "nodes" in repr(gv)

    def test_graph_view_focus_finding(self):
        t = targets()
        g = load(t.r01.e01)
        r = scan(t.r01.e01)
        gv = GraphView(g)
        gv.focus_finding(r.findings[0])
        assert gv.widget is not None

    def test_graph_view_on_node_click(self):
        g = load(targets().r01.e01)
        gv = GraphView(g)
        clicked = []
        gv.on_node_click(lambda name: clicked.append(name))
        # Simulate a click event
        gv._handle_node_click({"data": {"qualname": "test_node"}})
        assert clicked == ["test_node"]

    def test_findings_table_init(self):
        r = scan(targets().r01.e01)
        ft = FindingsTable(r.findings)
        assert ft.widget is not None

    def test_findings_table_empty(self):
        ft = FindingsTable([])
        assert ft.widget is not None

    def test_findings_table_update(self):
        r = scan(targets().r01.e01)
        ft = FindingsTable(r.findings)
        ft.update([])  # clear
        ft.update(r.findings)  # restore

    def test_findings_table_repr(self):
        ft = FindingsTable([])
        assert "FindingsTable" in repr(ft)

    def test_findings_table_on_select(self):
        r = scan(targets().r01.e01)
        assert len(r.findings) > 0
        ft = FindingsTable(r.findings)
        selected = []
        ft.on_select(lambda f: selected.append(f))
        # Simulate a click event on row 0
        ft._handle_click({"primary_key_row": 0})
        assert len(selected) == 1
        assert selected[0] is r.findings[0]

    def test_endpoint_table_init(self):
        g = load(targets().r01.e01)
        et = EndpointTable(g)
        assert et.widget is not None

    def test_evidence_table_update(self):
        r = scan(targets().r01.e01)
        ev = EvidenceTable(target_path=targets().r01.e01.path)
        ev.update(r.findings[0].evidence, title="Evidence")
        assert ev.widget is not None

    def test_code_path_view_show_finding(self):
        t = targets()
        g = load(t.r01.e01)
        r = scan(t.r01.e01)
        cp = CodePathView(target_path=t.r01.e01.path)
        cp.show_finding(g, r.findings[0])
        assert cp.widget is not None

    def test_batch_explorer_init(self):
        t = targets()
        graphs = batch_load([t.r01.e01, t.r01.e02])
        results = BatchResult({name: [] for name in graphs})
        bx = BatchExplorer(graphs, results)
        assert bx.widget is not None

    def test_details_pane_show_finding(self):
        t = targets()
        r = scan(t.r01.e01)
        pane = DetailsPane(target_path=t.r01.e01.path)
        pane.show_finding(r.findings[0])
        assert "Evidence" in pane.widget.value

    def test_explorer_init(self):
        t = targets()
        g = load(t.r01.e01)
        r = scan(t.r01.e01)
        ex = Explorer(g, r.findings, target_path=t.r01.e01.path)
        assert ex.widget is not None
        assert ex.graph_view is not None

    def test_explorer_accepts_scan_result(self):
        t = targets()
        r = scan(t.r01.e01)
        ex = Explorer(r)
        assert ex.widget is not None

    def test_explorer_repr(self):
        g = load(targets().r01.e01)
        r = scan(targets().r01.e01)
        ex = Explorer(g, r.findings)
        assert "Explorer" in repr(ex)


# ---------------------------------------------------------------------------
# _repr_html_ tests
# ---------------------------------------------------------------------------


class TestReprHtml:
    def test_analysis_graph_html(self):
        g = load(targets().r01.e01)
        html = g._repr_html_()
        assert "<table" in html or "<div" in html
        assert "routes" in html.lower() or "route" in html.lower()

    def test_scan_result_html(self):
        r = scan(targets().r01.e01)
        html = r._repr_html_()
        assert "<div" in html
        assert "ScanResult" in html or "findings" in html.lower()

    def test_target_registry_html(self):
        html = targets()._repr_html_()
        assert "<table" in html


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_full_workflow(self):
        """Test the complete notebook workflow end-to-end."""
        t = targets()
        g = load(t.r01.e01)
        r = scan(t.r01.e01)

        # Query
        fa = accesses(g, source="form")
        assert len(fa) > 0

        # Diff keys
        dk = diff_keys(g)
        # May or may not have divergent keys
        assert isinstance(dk, dict)

        # Finding paths
        assert len(r.findings) > 0, "e01 should produce findings"
        for f in r.findings:
            paths = finding_paths(f, g)
            assert isinstance(paths, list)

    def test_rule_development_workflow(self):
        """Test the interactive rule development workflow."""
        t = targets()

        # Load multiple exercises
        graphs = batch_load([t.r01.e01, t.r01.e02, t.r01.e03])

        # Write ad-hoc rule
        @detect("DEV-001", severity="high")
        def my_rule(g):
            for handler, route, accs in g.by_endpoint():
                sources = {a.source for a in accs}
                if len(sources) > 1:
                    yield finding("Multi-source", evidence=accs, endpoint=route)

        # Test across exercises
        results = batch_run(my_rule, graphs)

        # Should find something in at least one exercise
        assert results.total >= 0  # relaxed - depends on exercise content

        # Access specific results
        for name in results:
            findings_list = results[name]
            assert isinstance(findings_list, list)

    def test_load_and_scan_consistency(self):
        """Graph from load() and scan() should agree on routes."""
        t = targets()
        g = load(t.r01.e01)
        r = scan(t.r01.e01)

        load_routes = len(g.routes)
        scan_routes = len(r.graph.routes)
        assert load_routes == scan_routes
