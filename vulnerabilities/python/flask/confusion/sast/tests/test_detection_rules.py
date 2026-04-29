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

    def test_no_finding_single_fallback_site(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/checkout")
            def checkout():
                user_data = request.json if request.is_json else request.form
                tip = user_data.get("tip")
        ''', ["CONF-001"])
        assert len(findings) == 0

    def test_two_fallback_policies_detected(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/checkout")
            def checkout():
                first_data = request.json if request.is_json else request.form
                validated_tip = first_data.get("tip")

                second_data = request.json if request.is_json else request.args
                effective_tip = second_data.get("tip")
        ''', ["CONF-001"])
        assert len(findings) == 1
        assert "tip" in findings[0].title
        assert findings[0].details["pair_count"] >= 1

    def test_equivalent_reversed_fallback_policy_ignored(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/profile")
            def profile():
                primary_data = request.json if request.is_json else request.form
                checked_email = primary_data.get("email")

                secondary_data = request.form if not request.is_json else request.json
                effective_email = secondary_data.get("email")
        ''', ["CONF-001"])
        assert len(findings) == 0

    def test_precedence_policy_difference_detected(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/coupon")
            def coupon():
                validated_coupon = request.args.get("coupon") or request.form.get("coupon")
                effective_coupon = request.form.get("coupon") or request.args.get("coupon")
        ''', ["CONF-001"])
        assert len(findings) == 1
        assert "coupon" in findings[0].title

    def test_restx_resource_sibling_methods_are_isolated(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import request
            from flask_restx import Namespace, Resource

            ns = Namespace("orders")

            @ns.route("/orders")
            class Orders(Resource):
                def get(self):
                    item = request.args.get("item")
                    return item

                def post(self):
                    item = request.form.get("item")
                    return item
        ''', ["CONF-001"])
        assert len(findings) == 0


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
    def test_values_with_form_different_keys_is_info_signal(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/order")
            def create():
                a = request.form.get("x")
                b = request.values.get("y")
        ''', ["CONF-004"])
        assert len(findings) == 1
        assert findings[0].severity == Severity.INFO
        assert findings[0].details["signal"] == "mixed_key_values_usage"

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
        assert findings[0].severity == Severity.MEDIUM
        assert findings[0].details["signal"] == "same_key_values_pair"

    def test_values_without_specific_source_is_clean(self, scan_and_detect):
        findings = scan_and_detect('''
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.get("/search")
            def search():
                q = request.values.get("q")
        ''', ["CONF-004"])
        assert len(findings) == 0


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

    def test_e03_order_overwrite_not_input_source_confusion(self, r01_root, scan_exercise):
        findings = scan_exercise(r01_root / "e03_order_overwrite", ["CONF-001"])
        assert len(findings) == 0

    def test_e04_negative_tip_currently_expected_miss(self, r01_root, scan_exercise):
        findings = scan_exercise(r01_root / "e04_negative_tip", ["CONF-001"])
        assert len(findings) == 0
