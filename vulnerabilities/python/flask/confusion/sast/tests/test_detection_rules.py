"""Tests for confusion detection rules."""

import textwrap
from pathlib import Path

import pytest

from confusion_sast.backends.ast_backend import ASTBackend
from confusion_sast.analysis.graph import build_analysis_graph
from confusion_sast.detection.rules import run_rules
from confusion_sast.models import Severity


@pytest.fixture
def backend():
    return ASTBackend()


@pytest.fixture
def scan_and_detect(backend, tmp_path):
    """Helper to scan code and run detection rules."""
    def _scan(code: str, rules: list[str] | None = None):
        p = tmp_path / "app.py"
        p.write_text(textwrap.dedent(code))
        result = backend.extract(tmp_path)
        graph = build_analysis_graph(result)
        return run_rules(graph, rules)
    return _scan


class TestCONF001DualSourceConfusion:
    def test_same_key_different_sources(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/order")
            def create():
                name = request.args.get("name")
                val = request.form.get("name")
        ''', ["CONF-001"])
        assert len(findings) == 1
        assert findings[0].rule_id == "CONF-001"
        assert "'name'" in findings[0].title

    def test_no_finding_same_source(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/order")
            def create():
                name = request.form.get("name")
                val = request.form.get("name")
        ''', ["CONF-001"])
        assert len(findings) == 0

    def test_propagated_source_divergence(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            def check(data):
                return data.getlist("items")

            @bp.post("/order")
            def create():
                check(request.form)
                check(request.values)
        ''', ["CONF-001"])
        assert len(findings) == 1
        assert "items" in findings[0].title


class TestCONF002DualParameterConfusion:
    def test_singular_plural_keys(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/order")
            def create():
                single = request.form.get("item")
                multi = request.form.getlist("items")
        ''', ["CONF-002"])
        assert len(findings) == 1
        assert "'item'" in findings[0].title and "'items'" in findings[0].title

    def test_no_finding_unrelated_keys(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/order")
            def create():
                name = request.form.get("name")
                email = request.form.get("email")
        ''', ["CONF-002"])
        assert len(findings) == 0


class TestCONF003CardinalityConfusion:
    def test_get_vs_getlist_same_key(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/order")
            def create():
                first = request.form.get("items")
                all_items = request.form.getlist("items")
        ''', ["CONF-003"])
        assert len(findings) == 1
        assert "items" in findings[0].title

    def test_no_finding_same_accessor(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/order")
            def create():
                a = request.form.getlist("items")
                b = request.form.getlist("items")
        ''', ["CONF-003"])
        assert len(findings) == 0


class TestCONF004ValuesMergeConfusion:
    def test_values_with_form(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/order")
            def create():
                a = request.form.get("x")
                b = request.values.get("y")
        ''', ["CONF-004"])
        assert len(findings) == 1

    def test_values_with_args(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.get("/search")
            def search():
                a = request.args.get("q")
                b = request.values.get("q")
        ''', ["CONF-004"])
        assert len(findings) == 1


class TestCONF005DictMergeOverwrite:
    def test_user_data_merge(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/checkout")
            def checkout():
                user_data = request.json
                safe_data = {"total": 100, "user_id": 1}
                merged = {**user_data, **safe_data}
        ''', ["CONF-005"])
        assert len(findings) == 1

    def test_no_finding_no_user_data(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/checkout")
            def checkout():
                a = {"x": 1}
                b = {"y": 2}
                merged = {**a, **b}
        ''', ["CONF-005"])
        assert len(findings) == 0


class TestCONF007ConditionalSourceSelection:
    def test_ternary_source_with_merge(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/checkout")
            def checkout():
                user_data = request.json if request.is_json else request.form
                safe = {"total": 100}
                val = user_data.get("tip")
                merged = {**user_data, **safe}
        ''', ["CONF-007"])
        assert len(findings) == 1


class TestWebappIntegration:
    """Validate detection against known vulnerable exercises."""

    @pytest.fixture
    def scan_exercise(self, backend):
        def _scan(exercise_path: Path, rules: list[str] | None = None):
            result = backend.extract(exercise_path)
            graph = build_analysis_graph(result)
            return run_rules(graph, rules)
        return _scan

    def test_e00_baseline_clean(self, r01_root, scan_exercise):
        findings = scan_exercise(r01_root / "e00_baseline")
        # Baseline should have no high-severity findings
        high = [f for f in findings if f.severity in (Severity.HIGH, Severity.CRITICAL)]
        assert len(high) == 0

    def test_e01_dual_parameter_detected(self, r01_root, scan_exercise):
        findings = scan_exercise(r01_root / "e01_dual_parameter", ["CONF-002"])
        assert len(findings) >= 1
        assert any("item" in f.title and "items" in f.title for f in findings)

    def test_e02_delivery_fee_detected(self, r01_root, scan_exercise):
        findings = scan_exercise(r01_root / "e02_delivery_fee", ["CONF-001"])
        assert len(findings) >= 1
        assert any("form" in f.details.get("sources", []) for f in findings)

    def test_e02_values_merge_detected(self, r01_root, scan_exercise):
        findings = scan_exercise(r01_root / "e02_delivery_fee", ["CONF-004"])
        assert len(findings) >= 1

    def test_e03_dict_merge_detected(self, r01_root, scan_exercise):
        findings = scan_exercise(r01_root / "e03_order_overwrite", ["CONF-005"])
        assert len(findings) >= 1

    def test_e04_ternary_source_detected(self, r01_root, scan_exercise):
        findings = scan_exercise(r01_root / "e04_negative_tip", ["CONF-001"])
        assert len(findings) >= 1
        assert any("tip" in f.title for f in findings)
