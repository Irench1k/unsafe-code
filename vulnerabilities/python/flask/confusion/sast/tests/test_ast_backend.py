"""Tests for the AST backend extraction."""

import textwrap

import pytest
from confusion_sast.analysis.graph import build_analysis_graph
from confusion_sast.backends.ast_backend import ASTBackend
from confusion_sast.models import AccessorKind, InputSource, RouteKind


@pytest.fixture
def backend():
    return ASTBackend()


@pytest.fixture
def scan_snippet(backend, tmp_path):
    """Helper to scan a code snippet and return the extraction result."""

    def _scan(code: str, filename: str = "app.py"):
        p = tmp_path / filename
        p.write_text(textwrap.dedent(code))
        return backend.extract(tmp_path)

    return _scan


class TestRouteExtraction:
    def test_decorator_route(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint
            bp = Blueprint("test", __name__)

            @bp.route("/orders", methods=["POST"])
            def create_order():
                pass
        """)
        assert len(result.routes) == 1
        r = result.routes[0]
        assert r.handler_name == "create_order"
        assert r.route_kind == RouteKind.DECORATOR
        assert r.rule == "/orders"
        assert r.methods == ("POST",)

    def test_shorthand_decorators(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint
            bp = Blueprint("test", __name__)

            @bp.get("/items")
            def list_items():
                pass

            @bp.post("/items")
            def create_item():
                pass
        """)
        assert len(result.routes) == 2
        assert result.routes[0].methods == ("GET",)
        assert result.routes[1].methods == ("POST",)

    def test_multiple_methods(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint
            bp = Blueprint("test", __name__)

            @bp.route("/data", methods=["GET", "POST", "PUT"])
            def handle_data():
                pass
        """)
        assert result.routes[0].methods == ("GET", "POST", "PUT")


class TestInputAccessExtraction:
    def test_direct_request_args_get(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.route("/search")
            def search():
                query = request.args.get("q")
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "q"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.ARGS
        assert accesses[0].accessor == AccessorKind.GET

    def test_request_form_getlist(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/orders")
            def create_order():
                items = request.form.getlist("items")
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "items"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.FORM
        assert accesses[0].accessor == AccessorKind.GETLIST

    def test_request_values_get(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                val = request.values.get("key")
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "key"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.VALUES

    def test_subscript_access(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                val = request.form["name"]
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "name"]
        assert len(accesses) == 1
        assert accesses[0].accessor == AccessorKind.INDEX

    def test_alias_tracking(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                data = request.form
                val = data.get("name")
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "name"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.FORM

    def test_ternary_alias(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                data = request.json if request.is_json else request.form
                val = data.get("key")
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "key"]
        assert len(accesses) == 2
        sources = {a.source for a in accesses}
        assert sources == {InputSource.JSON, InputSource.FORM}


class TestSourcePropagation:
    def test_propagate_through_function_param(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            def process(data):
                return data.get("item")

            @bp.post("/orders")
            def create_order():
                process(request.form)
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "item"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.FORM
        assert "propagated" in accesses[0].notes[0]

    def test_propagate_multiple_sources(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            def check(data):
                return data.getlist("items")

            @bp.post("/orders")
            def create_order():
                check(request.form)
                check(request.values)
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "items"]
        assert len(accesses) == 2
        sources = {a.source for a in accesses}
        assert InputSource.FORM in sources
        assert InputSource.VALUES in sources


class TestDictMergeDetection:
    def test_dict_unpack_merge(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                user_data = request.json
                safe_data = {"total": 100}
                merged = {**user_data, **safe_data}
        """)
        assert len(result.dict_merges) == 1
        assert "user_data" in result.dict_merges[0].sources
        assert "safe_data" in result.dict_merges[0].sources


class TestBeforeRequestDetection:
    def test_before_request(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint
            bp = Blueprint("test", __name__)

            @bp.before_request
            def middleware():
                pass
        """)
        assert len(result.before_requests) == 1
        assert result.before_requests[0].blueprint == "bp"


class TestImportAliases:
    """Pattern 1: import aliases for flask.request."""

    def test_from_flask_import_request_as_alias(self, scan_snippet):
        result = scan_snippet("""
            from flask import request as req
            from flask import Blueprint
            bp = Blueprint("test", __name__)

            @bp.route("/search")
            def search():
                query = req.args.get("q")
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "q"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.ARGS
        assert accesses[0].accessor == AccessorKind.GET

    def test_import_flask_module_qualified(self, scan_snippet):
        result = scan_snippet("""
            import flask
            bp = flask.Blueprint("test", __name__)

            @bp.route("/search")
            def search():
                query = flask.request.args.get("q")
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "q"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.ARGS

    def test_import_flask_as_alias(self, scan_snippet):
        result = scan_snippet("""
            import flask as fl
            bp = fl.Blueprint("test", __name__)

            @bp.route("/data")
            def handle():
                val = fl.request.form["name"]
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "name"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.FORM
        assert accesses[0].accessor == AccessorKind.INDEX

    def test_alias_get_json(self, scan_snippet):
        result = scan_snippet("""
            from flask import request as req
            from flask import Blueprint
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                data = req.get_json()
        """)
        accesses = [a for a in result.input_accesses if a.source == InputSource.JSON]
        assert len(accesses) == 1
        assert accesses[0].accessor == AccessorKind.DIRECT

    def test_module_qualified_get_json(self, scan_snippet):
        result = scan_snippet("""
            import flask
            bp = flask.Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                data = flask.request.get_json()
        """)
        accesses = [a for a in result.input_accesses if a.source == InputSource.JSON]
        assert len(accesses) == 1

    def test_alias_subscript_access(self, scan_snippet):
        result = scan_snippet("""
            from flask import request as r
            from flask import Blueprint
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                val = r.form["name"]
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "name"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.FORM

    def test_alias_variable_assignment(self, scan_snippet):
        result = scan_snippet("""
            from flask import request as req
            from flask import Blueprint
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                data = req.form
                val = data.get("name")
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "name"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.FORM


class TestAddUrlRule:
    """Pattern 2: app.add_url_rule() route registration."""

    def test_add_url_rule_with_view_func_keyword(self, scan_snippet):
        result = scan_snippet("""
            from flask import Flask
            app = Flask(__name__)

            def handle_data():
                pass

            app.add_url_rule("/data", view_func=handle_data)
        """)
        assert len(result.routes) == 1
        r = result.routes[0]
        assert r.handler_name == "handle_data"
        assert r.rule == "/data"
        assert r.route_kind == RouteKind.ADD_URL_RULE
        assert r.methods == ("GET",)

    def test_add_url_rule_positional_args(self, scan_snippet):
        result = scan_snippet("""
            from flask import Flask
            app = Flask(__name__)

            def handler():
                pass

            app.add_url_rule("/path", "endpoint_name", handler)
        """)
        assert len(result.routes) == 1
        assert result.routes[0].handler_name == "handler"
        assert result.routes[0].rule == "/path"

    def test_add_url_rule_with_methods(self, scan_snippet):
        result = scan_snippet("""
            from flask import Flask
            app = Flask(__name__)

            def create():
                pass

            app.add_url_rule("/items", view_func=create, methods=["POST", "PUT"])
        """)
        assert len(result.routes) == 1
        assert result.routes[0].methods == ("POST", "PUT")


class TestMethodView:
    """Pattern 3: MethodView class-based views."""

    def test_method_view_basic(self, scan_snippet):
        result = scan_snippet("""
            from flask import Flask
            from flask.views import MethodView
            app = Flask(__name__)

            class UserAPI(MethodView):
                def get(self):
                    return "list"

                def post(self):
                    return "create"

            app.add_url_rule("/users", view_func=UserAPI.as_view("user_api"))
        """)
        assert len(result.routes) == 2
        methods = {r.methods[0] for r in result.routes}
        assert methods == {"GET", "POST"}
        for r in result.routes:
            assert r.route_kind == RouteKind.METHOD_VIEW
            assert r.rule == "/users"

    def test_method_view_with_input_access(self, scan_snippet):
        result = scan_snippet("""
            from flask import Flask, request
            from flask.views import MethodView
            app = Flask(__name__)

            class ItemAPI(MethodView):
                def get(self):
                    query = request.args.get("q")
                    return query

                def post(self):
                    name = request.form.get("name")
                    return name

            app.add_url_rule("/items", view_func=ItemAPI.as_view("item_api"))
        """)
        accesses = [a for a in result.input_accesses if a.key_literal]
        assert len(accesses) == 2
        keys = {a.key_literal for a in accesses}
        assert keys == {"q", "name"}
        sources = {a.key_literal: a.source for a in accesses}
        assert sources["q"] == InputSource.ARGS
        assert sources["name"] == InputSource.FORM

    def test_method_view_all_verbs(self, scan_snippet):
        result = scan_snippet("""
            from flask.views import MethodView
            from flask import Flask
            app = Flask(__name__)

            class FullAPI(MethodView):
                def get(self): pass
                def post(self): pass
                def put(self): pass
                def patch(self): pass
                def delete(self): pass

            app.add_url_rule("/resource", view_func=FullAPI.as_view("full_api"))
        """)
        assert len(result.routes) == 5
        methods = {r.methods[0] for r in result.routes}
        assert methods == {"GET", "POST", "PUT", "PATCH", "DELETE"}


class TestMultiLevelPropagation:
    """Pattern 4: Multi-level parameter propagation."""

    def test_two_level_propagation(self, scan_snippet):
        """A -> B -> C: A passes request.form to B, B forwards to C."""
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            def validate(data):
                return data.get("key")

            def process(payload):
                validate(payload)

            @bp.post("/submit")
            def submit():
                process(request.form)
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "key"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.FORM
        assert "propagated" in accesses[0].notes[0]

    def test_three_level_propagation(self, scan_snippet):
        """A -> B -> C -> D: three levels of parameter forwarding."""
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            def deep(d):
                return d.get("value")

            def middle(m):
                deep(m)

            def outer(o):
                middle(o)

            @bp.post("/submit")
            def submit():
                outer(request.form)
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "value"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.FORM

    def test_propagation_does_not_infinite_loop(self, scan_snippet):
        """Mutual recursion should not hang — capped at max iterations."""
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            def ping(data):
                pong(data)
                return data.get("key")

            def pong(data):
                ping(data)

            @bp.post("/submit")
            def submit():
                ping(request.form)
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "key"]
        assert len(accesses) >= 1
        assert accesses[0].source == InputSource.FORM


class TestCallGraphPrecision:
    def test_request_accessor_method_does_not_resolve_to_unrelated_project_method(
        self, scan_snippet
    ):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/integrations")
            def integrations():
                name = request.values.get("name")
                return name

            class ChallengeList:
                def get(self):
                    view = request.args.get("view")
                    return view
        """)
        graph = build_analysis_graph(result)
        route = result.routes[0]

        reachable_accesses = graph.accesses_reachable_from(route.handler_qualname)
        reachable_keys = {(a.source, a.key_literal) for a in reachable_accesses}

        assert (InputSource.VALUES, "name") in reachable_keys
        assert (InputSource.ARGS, "view") not in reachable_keys
        assert not graph.call_edges_between(
            "app.integrations",
            "app.ChallengeList.get",
        )


class TestClassHandlerLifecycle:
    def test_add_url_rule_class_handler_reaches_lifecycle_methods(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            class RH:
                def process(self):
                    self._process_args()
                    return self._process()

            class RHMoveThing(RH):
                def _process_args(self):
                    checked_id = request.form.get("target_id")
                    self.ids = request.values.getlist("thing_id")

                def _process(self):
                    return {"ids": self.ids}

            bp.add_url_rule("/move", "move", RHMoveThing, methods=("POST",))
        """)
        graph = build_analysis_graph(result)
        route = result.routes[0]

        assert route.handler_qualname == "app.RHMoveThing"
        assert "class_handler" in route.notes
        assert "app.RHMoveThing._process_args" in graph.reachable_from(
            route.handler_qualname
        )

        reachable_keys = {
            (a.source, a.accessor, a.key_literal)
            for a in graph.accesses_reachable_from(route.handler_qualname)
        }
        assert (InputSource.FORM, AccessorKind.GET, "target_id") in reachable_keys
        assert (InputSource.VALUES, AccessorKind.GETLIST, "thing_id") in reachable_keys

    def test_add_url_rule_resolves_imported_class_handler_alias(self, backend, tmp_path):
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")
        (app_dir / "controllers.py").write_text(
            textwrap.dedent("""
            from flask import request

            class RH:
                def process(self):
                    return self._process()

            class RHMoveThing(RH):
                def _process_args(self):
                    self.target_id = request.form.get("target_id")

                def _process(self):
                    return request.values.getlist("thing_id")
        """)
        )
        (app_dir / "blueprint.py").write_text(
            textwrap.dedent("""
            from flask import Blueprint
            from app.controllers import RHMoveThing

            bp = Blueprint("test", __name__)
            bp.add_url_rule("/move", "move", RHMoveThing, methods=("POST",))
        """)
        )

        result = backend.extract(tmp_path)
        graph = build_analysis_graph(result)
        route = result.routes[0]

        assert route.handler_qualname == "app.controllers.RHMoveThing"
        assert "app.controllers.RHMoveThing._process_args" in graph.reachable_from(
            route.handler_qualname
        )
        reachable_keys = {
            (a.source, a.key_literal)
            for a in graph.accesses_reachable_from(route.handler_qualname)
        }
        assert (InputSource.FORM, "target_id") in reachable_keys
        assert (InputSource.VALUES, "thing_id") in reachable_keys


class TestFlaskRestXResources:
    def test_namespace_route_resource_methods_are_endpoints(self, scan_snippet):
        result = scan_snippet("""
            from flask import request
            from flask_restx import Namespace, Resource

            ns = Namespace("challenges")

            @ns.route("")
            class ChallengeList(Resource):
                def get(self):
                    view = request.args.get("view")
                    return view

                def post(self):
                    data = request.get_json()
                    name = data.get("name")
                    return name
        """)
        graph = build_analysis_graph(result)
        routes = {route.handler_qualname: route for route in result.routes}

        assert set(routes) == {"app.ChallengeList.get", "app.ChallengeList.post"}
        assert routes["app.ChallengeList.get"].methods == ("GET",)
        assert routes["app.ChallengeList.post"].methods == ("POST",)
        assert routes["app.ChallengeList.get"].rule == ""
        assert routes["app.ChallengeList.get"].blueprint == "ns"
        assert "framework:flask-restx-resource" in routes["app.ChallengeList.get"].notes

        get_keys = {
            (access.source, access.key_literal)
            for access in graph.accesses_reachable_from("app.ChallengeList.get")
        }
        post_keys = {
            (access.source, access.key_literal)
            for access in graph.accesses_reachable_from("app.ChallengeList.post")
        }
        assert (InputSource.ARGS, "view") in get_keys
        assert (InputSource.JSON, "name") not in get_keys
        assert (InputSource.JSON, "name") in post_keys
        assert (InputSource.ARGS, "view") not in post_keys

    def test_namespace_route_resource_alias(self, scan_snippet):
        result = scan_snippet("""
            from flask import request
            from flask_restx import Namespace, Resource as ApiResource

            ns = Namespace("users")

            @ns.route("/users")
            class UserList(ApiResource):
                def get(self):
                    q = request.args.get("q")
                    return q
        """)

        assert len(result.routes) == 1
        route = result.routes[0]
        assert route.handler_qualname == "app.UserList.get"
        assert route.methods == ("GET",)
        assert "resource_base:unresolved" not in route.notes

    def test_add_resource_resolves_local_resource_methods(self, scan_snippet):
        result = scan_snippet("""
            from flask import request
            from flask_restx import Api, Resource

            api = Api()

            class TeamList(Resource):
                def get(self):
                    q = request.args.get("q")
                    return q

                def post(self):
                    data = request.get_json()
                    name = data.get("name")
                    return name

            api.add_resource(TeamList, "/teams")
        """)

        routes = {route.handler_qualname: route for route in result.routes}
        assert set(routes) == {"app.TeamList.get", "app.TeamList.post"}
        assert routes["app.TeamList.get"].rule == "/teams"
        assert routes["app.TeamList.post"].methods == ("POST",)
        assert "registration:add_resource" in routes["app.TeamList.get"].notes

    def test_add_resource_resolves_imported_resource_class(self, backend, tmp_path):
        app_dir = tmp_path / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")
        (app_dir / "resources.py").write_text(
            textwrap.dedent("""
            from flask import request
            from flask_restx import Resource

            class UserList(Resource):
                def get(self):
                    q = request.args.get("q")
                    return q
        """)
        )
        (app_dir / "api.py").write_text(
            textwrap.dedent("""
            from flask_restx import Api
            from app.resources import UserList

            api = Api()
            api.add_resource(UserList, "/users")
        """)
        )

        result = backend.extract(tmp_path)
        graph = build_analysis_graph(result)

        assert len(result.routes) == 1
        route = result.routes[0]
        assert route.handler_qualname == "app.resources.UserList.get"
        assert route.rule == "/users"
        assert (InputSource.ARGS, "q") in {
            (access.source, access.key_literal)
            for access in graph.accesses_reachable_from(route.handler_qualname)
        }


class TestGetJsonKwargs:
    """Pattern 5: get_json() with keyword arguments."""

    def test_get_json_with_silent(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                data = request.get_json(silent=True)
        """)
        accesses = [a for a in result.input_accesses if a.source == InputSource.JSON]
        assert len(accesses) == 1
        assert accesses[0].accessor == AccessorKind.DIRECT

    def test_get_json_with_multiple_kwargs(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                data = request.get_json(force=True, silent=True, cache=False)
        """)
        accesses = [a for a in result.input_accesses if a.source == InputSource.JSON]
        assert len(accesses) == 1

    def test_get_json_or_pattern(self, scan_snippet):
        result = scan_snippet("""
            from flask import Blueprint, request
            bp = Blueprint("test", __name__)

            @bp.post("/data")
            def handle():
                payload = request.get_json(silent=True) or {}
                val = payload.get("key")
        """)
        accesses = [a for a in result.input_accesses if a.key_literal == "key"]
        assert len(accesses) == 1
        assert accesses[0].source == InputSource.JSON


class TestWebappIntegration:
    """Integration tests against the actual webapp exercises."""

    def test_e00_baseline_no_routes_with_confusion(self, r01_root, backend):
        result = backend.extract(r01_root / "e00_baseline")
        assert len(result.routes) > 0  # has routes
        # Should have no confusion patterns
        form_accesses = [a for a in result.input_accesses if a.source == InputSource.FORM]
        values_accesses = [a for a in result.input_accesses if a.source == InputSource.VALUES]
        # Baseline should not mix form and values
        assert not values_accesses or not form_accesses

    def test_e01_dual_parameter_extracts_item_and_items(self, r01_root, backend):
        result = backend.extract(r01_root / "e01_dual_parameter")
        keys = {a.key_literal for a in result.input_accesses if a.key_literal}
        assert "item" in keys
        assert "items" in keys

    def test_e02_extracts_form_and_values(self, r01_root, backend):
        result = backend.extract(r01_root / "e02_delivery_fee")
        sources = {a.source for a in result.input_accesses}
        assert InputSource.FORM in sources
        assert InputSource.VALUES in sources
