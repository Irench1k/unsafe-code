"""Tests for REPL helpers and detection toolkit."""

import textwrap
from pathlib import Path

import pytest

from confusion_sast.backends.ast_backend import ASTBackend
from confusion_sast.analysis.graph import build_analysis_graph
from confusion_sast.detection.toolkit import detect, finding, run_fn, run_rule
from confusion_sast.models import InputSource, Severity
from confusion_sast.pipeline import extract, scan
from confusion_sast.repl import accesses, diff_keys, endpoint_detail, routes


@pytest.fixture
def backend():
    return ASTBackend()


@pytest.fixture
def e01_graph(r01_root):
    return extract(r01_root / "e01_dual_parameter")


@pytest.fixture
def e01_scan(r01_root):
    return scan(r01_root / "e01_dual_parameter")


class TestExtractReturnsGraph:
    def test_extract_returns_analysis_graph(self, e01_graph):
        assert hasattr(e01_graph, "stats")
        assert hasattr(e01_graph, "by_endpoint")
        assert e01_graph.stats()["routes"] > 0

    def test_multiple_graphs_independent(self, r01_root):
        g1 = extract(r01_root / "e01_dual_parameter")
        g2 = extract(r01_root / "e02_delivery_fee")
        assert g1.stats()["routes"] > 0
        assert g2.stats()["routes"] > 0
        assert g1 is not g2
        assert g1.stats() != g2.stats()


class TestGraphQueryHelpers:
    def test_by_endpoint(self, e01_graph):
        endpoints = e01_graph.by_endpoint()
        assert len(endpoints) > 0
        handler, route, accs = endpoints[0]
        assert isinstance(handler, str)

    def test_by_key(self, e01_graph):
        keys = e01_graph.by_key()
        assert "item" in keys or "items" in keys

    def test_sources_for(self, e01_graph):
        for handler, route, accs in e01_graph.by_endpoint():
            if "create_new_order" in handler:
                sources = e01_graph.sources_for(handler)
                assert InputSource.FORM in sources

    def test_stats(self, e01_graph):
        s = e01_graph.stats()
        assert s["routes"] > 0
        assert s["nodes"] > 0
        assert s["edges"] > 0


class TestReplDataReturns:
    def test_routes_returns_list(self, e01_scan):
        r = routes(e01_scan)
        assert isinstance(r, list)
        assert len(r) > 0

    def test_accesses_returns_filtered_list(self, e01_scan):
        form_accesses = accesses(e01_scan, source="form")
        assert isinstance(form_accesses, list)
        all_accesses = accesses(e01_scan)
        assert len(form_accesses) <= len(all_accesses)

    def test_accesses_filter_by_key(self, e01_scan):
        item_accesses = accesses(e01_scan, key="item")
        assert all(a.key_literal == "item" for a in item_accesses)

    def test_endpoint_detail_returns_dict(self, e01_scan):
        detail = endpoint_detail("create_new_order", e01_scan)
        assert isinstance(detail, dict)
        assert len(detail) > 0
        for h, d in detail.items():
            assert "route" in d
            assert "accesses" in d
            assert "sources" in d
            assert "keys" in d

    def test_diff_keys_returns_divergent(self, r01_root):
        r = scan(r01_root / "e02_delivery_fee")
        dk = diff_keys(r)
        assert isinstance(dk, dict)
        # e02 has "items" from both form and values
        if "items" in dk:
            assert len(dk["items"]["sources"]) > 1


class TestDetectionToolkit:
    def test_finding_builder(self):
        f = finding("test title", severity="high")
        assert f.title == "test title"
        assert f.severity == Severity.HIGH
        assert f.rule_id == "ADHOC"

    def test_finding_auto_location(self, e01_scan):
        evs = accesses(e01_scan, source="form", key="item")
        if evs:
            f = finding("test", evidence=evs)
            assert f.location.line > 0

    def test_detect_decorator(self, e01_graph):
        @detect("TEST-001", severity="high")
        def my_rule(g):
            for handler, route, accs in g.by_endpoint():
                if len(accs) > 2:
                    yield finding("many accesses", evidence=accs, endpoint=route)

        results = run_fn(my_rule, e01_graph)
        assert isinstance(results, list)
        for f in results:
            assert f.rule_id == "TEST-001"
            assert f.severity == Severity.HIGH

    def test_run_rule_by_id(self, e01_graph):
        results = run_rule("CONF-002", e01_graph)
        assert len(results) >= 1

    def test_detect_does_not_register_by_default(self, e01_graph):
        from confusion_sast.detection.rules import _RULES
        initial_count = len(_RULES)

        @detect("TEMP-999")
        def temp_rule(g):
            yield finding("temp")

        assert len(_RULES) == initial_count
