"""Pure Python AST-based code analysis backend.

No external tools required. Walks Python source files using the stdlib `ast`
module to extract routes, input accesses, call edges, and merge patterns.

This is the primary backend for fast iteration and testing. It handles all
patterns that are syntactically visible (which covers the majority of Flask
confusion vulnerabilities).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
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
from .interface import ExtractionResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ROUTE_DECORATORS = {"route", "get", "post", "put", "patch", "delete"}

_HTTP_VERB_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")
_HTTP_VERBS = set(_HTTP_VERB_METHODS)

# Maps request attribute -> InputSource. The request object name is resolved
# dynamically via _flask_request_names (to support import aliases).
_REQUEST_ATTR_SOURCE_MAP: dict[str, InputSource] = {
    "args": InputSource.ARGS,
    "form": InputSource.FORM,
    "values": InputSource.VALUES,
    "json": InputSource.JSON,
    "data": InputSource.DATA,
    "headers": InputSource.HEADERS,
    "cookies": InputSource.COOKIES,
    "files": InputSource.FILES,
}

_DATA_ACCESSOR_METHODS = {
    "get",
    "getlist",
    "items",
    "keys",
    "values",
    "lists",
    "to_dict",
    "get_json",
}

_COMMON_NON_PROJECT_CALLS = {
    "abort",
    "dict",
    "flash",
    "int",
    "jsonify",
    "len",
    "list",
    "print",
    "redirect",
    "render_template",
    "set",
    "sorted",
    "str",
    "tuple",
}

_CLASS_HANDLER_LIFECYCLE_METHODS = (
    "process",
    "_check_csrf",
    "_do_process",
    "_process_args",
    "_check_access",
    "_process",
    "_process_GET",
    "_process_POST",
    "_process_PATCH",
    "_process_PUT",
    "_process_DELETE",
)


@dataclass(frozen=True)
class _ResourceRouteRegistration:
    class_name: str
    class_qualname: str
    rule: str | None
    blueprint: str | None
    location: Location
    raw_code: str
    notes: tuple[str, ...]


# ---------------------------------------------------------------------------
# AST Helpers
# ---------------------------------------------------------------------------


def _unparse_safe(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "<unparseable>"


def _str_literal(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _module_qualname(file_path: str, project_root: str) -> str:
    """Convert a file path to a dotted module name."""
    rel = Path(file_path).relative_to(project_root)
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


# ---------------------------------------------------------------------------
# Extraction Visitors
# ---------------------------------------------------------------------------


class _FileVisitor(ast.NodeVisitor):
    """Visits a single Python file and extracts facts."""

    def __init__(self, file_path: str, module_name: str) -> None:
        self.file_path = file_path
        self.module = module_name
        self.routes: list[RouteFact] = []
        self.input_accesses: list[InputAccessFact] = []
        self.call_edges: list[CallEdge] = []
        self.before_requests: list[BeforeRequestFact] = []
        self.dict_merges: list[DictMergeFact] = []
        self._current_function: str | None = None
        self._current_class: str | None = None
        self._request_aliases: dict[str, InputSource] = {}
        self._local_aliases: dict[str, str] = {}  # local_name -> "request.args" etc
        self._blueprint_names: set[str] = set()
        self._function_params: dict[str, list[str]] = {}  # qualname -> [param_names]
        self._ternary_aliases: dict[str, list[InputSource]] = {}
        # Accesses on function parameters (not yet resolved to a source)
        self._param_accesses: list[
            tuple[str, int, InputAccessFact]
        ] = []  # (func_qualname, param_idx, fact)
        # Parameter forwarding: (caller_qualname, caller_param_idx, callee_short_name, callee_arg_idx)
        # Tracks when a function passes its own parameter as an argument to another function.
        self._param_forwarding: list[tuple[str, int, str, int]] = []
        # Names that refer to the Flask request object (handles import aliases)
        self._flask_request_names: set[str] = {"request"}
        # Module aliases for `import flask as X` -> track "X" so we can match X.request.args
        self._flask_module_aliases: set[str] = {"flask"}
        # MethodView classes: class_name -> list of (verb, method_qualname)
        self._method_view_classes: dict[str, list[tuple[str, str]]] = {}
        # Local imported names: RHMoveThing -> app.controllers.RHMoveThing
        self._import_aliases: dict[str, str] = {}
        # Class metadata used by the backend to add conservative framework edges.
        self._class_qualnames: dict[str, str] = {}
        self._class_methods: dict[str, set[str]] = {}
        self._class_bases: dict[str, tuple[str, ...]] = {}
        self._resource_class_names: set[str] = {"Resource"}
        self._pending_resource_routes: list[_ResourceRouteRegistration] = []

    def _qualname(self, name: str) -> str:
        if self._current_class:
            return f"{self.module}.{self._current_class}.{name}"
        return f"{self.module}.{name}"

    def _loc(self, node: ast.AST) -> Location:
        return Location(
            file=self.file_path,
            line=getattr(node, "lineno", 0),
            col=getattr(node, "col_offset", 0),
        )

    # --- Import tracking ---

    def visit_Import(self, node: ast.Import) -> None:
        """Track `import flask` and `import flask as X`."""
        for alias in node.names:
            if alias.name in ("flask", "flask_restful"):
                name = alias.asname or alias.name
                self._flask_module_aliases.add(name)
            local_name = alias.asname or alias.name.split(".", 1)[0]
            self._import_aliases[local_name] = alias.name if alias.asname else local_name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track `from flask import request` and `from flask import request as req`."""
        if node.module in ("flask", "flask_restful"):
            for alias in node.names:
                if alias.name == "request":
                    name = alias.asname or alias.name
                    self._flask_request_names.add(name)
        if node.module in ("flask_restx", "flask_restful"):
            for alias in node.names:
                if alias.name == "Resource":
                    self._resource_class_names.add(alias.asname or alias.name)
        if node.module:
            for alias in node.names:
                if alias.name == "*":
                    continue
                self._import_aliases[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)

    # --- Top-level assignments (blueprint detection, aliases) ---

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Detect blueprint creation: bp = Blueprint(...)
                if isinstance(node.value, ast.Call):
                    func = node.value.func
                    if (
                        isinstance(func, ast.Name)
                        and func.id == "Blueprint"
                        or isinstance(func, ast.Attribute)
                        and func.attr == "Blueprint"
                    ):
                        self._blueprint_names.add(target.id)

                # Detect request source aliases: data = request.form
                self._check_request_alias_assign(target.id, node.value)

        self.generic_visit(node)

    def _check_request_alias_assign(self, name: str, value: ast.AST) -> None:
        source = self._resolve_input_source(value)
        if source is not None:
            self._local_aliases[name] = _unparse_safe(value)
            self._request_aliases[name] = source
            return

        # Handle ternary: user_data = request.json if request.is_json else request.form
        if isinstance(value, ast.IfExp):
            body_src = self._resolve_input_source(value.body)
            else_src = self._resolve_input_source(value.orelse)
            if body_src is not None or else_src is not None:
                self._local_aliases[name] = _unparse_safe(value)
                sources = []
                if body_src is not None:
                    sources.append(body_src)
                if else_src is not None:
                    sources.append(else_src)
                self._ternary_aliases[name] = sources
                if sources:
                    self._request_aliases[name] = sources[0]

        # Handle or-chain: payload = request.get_json(silent=True) or {}
        if isinstance(value, ast.BoolOp) and isinstance(value.op, ast.Or):
            for v in value.values:
                src = self._resolve_input_source(v)
                if src is not None:
                    self._local_aliases[name] = _unparse_safe(value)
                    self._request_aliases[name] = src
                    return

    # --- Function definitions ---

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_funcdef(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_funcdef(node)

    def _visit_funcdef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        old_function = self._current_function
        func_name = node.name
        qualname = self._qualname(func_name)
        self._current_function = qualname

        # Save and clear local aliases for this scope
        old_aliases = self._request_aliases.copy()
        old_local = self._local_aliases.copy()

        # Track function parameter names (excluding self/cls)
        params = []
        for arg in node.args.args:
            if arg.arg not in ("self", "cls"):
                params.append(arg.arg)
        self._function_params[qualname] = params

        # Analyze decorators
        self._analyze_decorators(node, qualname)

        # Walk function body
        self.generic_visit(node)

        # Restore
        self._current_function = old_function
        self._request_aliases = old_aliases
        self._local_aliases = old_local

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        old_class = self._current_class
        self._current_class = node.name
        class_qualname = f"{self.module}.{node.name}"
        self._class_qualnames[node.name] = class_qualname
        self._class_methods.setdefault(class_qualname, set())
        self._class_bases[class_qualname] = tuple(
            base_qualname
            for base in node.bases
            if (base_qualname := self._resolve_class_reference(base)) is not None
        )

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._class_methods[class_qualname].add(f"{class_qualname}.{item.name}")

        # Detect MethodView / View subclasses
        is_method_view = any(
            (isinstance(base, ast.Name) and base.id in ("MethodView", "View"))
            or (isinstance(base, ast.Attribute) and base.attr in ("MethodView", "View"))
            for base in node.bases
        )
        if is_method_view:
            verb_methods: list[tuple[str, str]] = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name in _HTTP_VERBS:
                        qualname = self._qualname(item.name)
                        verb_methods.append((item.name.upper(), qualname))
            if verb_methods:
                self._method_view_classes[node.name] = verb_methods

        self._analyze_resource_class_routes(node, class_qualname)

        self.generic_visit(node)
        self._current_class = old_class

    def _class_http_methods(
        self,
        class_qualname: str,
        body: list[ast.stmt],
    ) -> list[tuple[str, str]]:
        methods: list[tuple[str, str]] = []
        for item in body:
            if (
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name in _HTTP_VERBS
            ):
                methods.append((item.name.upper(), f"{class_qualname}.{item.name}"))
        return methods

    def _is_rest_resource_class(self, node: ast.ClassDef) -> bool:
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in self._resource_class_names:
                return True
            if (
                isinstance(base, ast.Attribute)
                and base.attr == "Resource"
                and isinstance(base.value, ast.Name)
            ):
                resolved = self._import_aliases.get(base.value.id, base.value.id)
                if resolved in {"flask_restx", "flask_restful"} or resolved.endswith(
                    (".flask_restx", ".flask_restful")
                ):
                    return True
        return False

    def _analyze_resource_class_routes(
        self,
        node: ast.ClassDef,
        class_qualname: str,
    ) -> None:
        """Detect Flask-RESTX/RESTful ``@namespace.route`` class resources."""
        http_methods = self._class_http_methods(class_qualname, node.body)
        if not http_methods:
            return

        is_resource = self._is_rest_resource_class(node)
        for dec in node.decorator_list:
            if (
                not isinstance(dec, ast.Call)
                or not isinstance(dec.func, ast.Attribute)
                or dec.func.attr != "route"
            ):
                continue

            # Class-level route decorators are the Flask-RESTX/RESTful shape.
            # Requiring HTTP verb methods keeps ordinary decorated classes from
            # becoming broad pseudo-endpoints.
            blueprint_name = (
                dec.func.value.id if isinstance(dec.func.value, ast.Name) else None
            )
            rule = _str_literal(dec.args[0]) if dec.args else None
            base_notes = [
                "framework:flask-restx-resource",
                f"resource_class:{node.name}",
            ]
            if not is_resource:
                base_notes.append("resource_base:unresolved")

            for verb, method_qualname in http_methods:
                self.routes.append(
                    RouteFact(
                        handler_name=method_qualname.rsplit(".", 1)[-1],
                        handler_qualname=method_qualname,
                        route_kind=RouteKind.ENDPOINT,
                        rule=rule,
                        methods=(verb,),
                        blueprint=blueprint_name,
                        location=self._loc(dec),
                        raw_code=_unparse_safe(dec),
                        notes=tuple(base_notes),
                    )
                )

    def _resolve_class_reference(self, node: ast.AST) -> str | None:
        """Resolve a class-like AST expression to a best-effort qualname."""
        if isinstance(node, ast.Name):
            return self._resolve_local_name(node.id)
        if isinstance(node, ast.Attribute):
            parts: list[str] = []
            current: ast.AST = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                root = self._import_aliases.get(current.id, current.id)
                return ".".join([root, *reversed(parts)])
        return None

    def _resolve_local_name(self, name: str) -> str:
        """Resolve an imported/local top-level symbol name to a project qualname."""
        if name in self._import_aliases:
            return self._import_aliases[name]
        return self._qualname(name)

    # --- Decorator analysis ---

    def _analyze_decorators(self, node: ast.FunctionDef, qualname: str) -> None:
        blueprint_name = None

        for dec in node.decorator_list:
            # @bp.route("/path", methods=["GET", "POST"])
            # @bp.get("/path"), @bp.post("/path"), etc.
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                attr_name = dec.func.attr
                if attr_name in _ROUTE_DECORATORS:
                    # Figure out blueprint name
                    if isinstance(dec.func.value, ast.Name):
                        blueprint_name = dec.func.value.id

                    rule = _str_literal(dec.args[0]) if dec.args else None
                    methods = self._extract_methods(dec, attr_name)

                    self.routes.append(
                        RouteFact(
                            handler_name=node.name,
                            handler_qualname=qualname,
                            route_kind=RouteKind.DECORATOR,
                            rule=rule,
                            methods=methods,
                            blueprint=blueprint_name,
                            location=self._loc(dec),
                            raw_code=_unparse_safe(dec),
                        )
                    )

            # @bp.before_request
            elif isinstance(dec, ast.Attribute) and dec.attr == "before_request":
                bp_name = None
                if isinstance(dec.value, ast.Name):
                    bp_name = dec.value.id
                self.before_requests.append(
                    BeforeRequestFact(
                        function_qualname=qualname,
                        blueprint=bp_name,
                        location=self._loc(dec),
                    )
                )

            # @bp.before_request (as call, e.g. @bp.before_request())
            elif (
                isinstance(dec, ast.Call)
                and isinstance(dec.func, ast.Attribute)
                and dec.func.attr == "before_request"
            ):
                bp_name = None
                if isinstance(dec.func.value, ast.Name):
                    bp_name = dec.func.value.id
                self.before_requests.append(
                    BeforeRequestFact(
                        function_qualname=qualname,
                        blueprint=bp_name,
                        location=self._loc(dec),
                    )
                )

    def _extract_methods(self, dec: ast.Call, attr_name: str) -> tuple[str, ...]:
        if attr_name != "route":
            return (attr_name.upper(),)

        for kw in dec.keywords:
            if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                methods = []
                for elt in kw.value.elts:
                    lit = _str_literal(elt)
                    if lit:
                        methods.append(lit.upper())
                if methods:
                    return tuple(sorted(set(methods)))

        return ("GET",)

    # --- add_url_rule detection ---

    def _check_add_url_rule(self, node: ast.Call) -> None:
        """Detect app.add_url_rule("/path", "endpoint", view_func) patterns."""
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_url_rule":
            return

        rule = _str_literal(node.args[0]) if node.args else None

        # Extract methods keyword
        methods = ("GET",)
        for kw in node.keywords:
            if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                m = []
                for elt in kw.value.elts:
                    lit = _str_literal(elt)
                    if lit:
                        m.append(lit.upper())
                if m:
                    methods = tuple(sorted(set(m)))

        # Find the view_func — 3rd positional arg or view_func= keyword
        view_func_node: ast.AST | None = None
        if len(node.args) >= 3:
            view_func_node = node.args[2]
        for kw in node.keywords:
            if kw.arg == "view_func":
                view_func_node = kw.value
                break

        if view_func_node is None:
            return

        # Case 1: Plain function reference — app.add_url_rule("/path", view_func=handler)
        if isinstance(view_func_node, ast.Name):
            handler_name = view_func_node.id
            handler_qualname = self._resolve_local_name(handler_name)
            notes: tuple[str, ...] = ()
            if handler_name in self._class_qualnames or handler_name[:1].isupper():
                notes = ("class_handler", "framework:add_url_rule")
            self.routes.append(
                RouteFact(
                    handler_name=handler_name,
                    handler_qualname=handler_qualname,
                    route_kind=RouteKind.ADD_URL_RULE,
                    rule=rule,
                    methods=methods,
                    blueprint=None,
                    location=self._loc(node),
                    raw_code=_unparse_safe(node),
                    notes=notes,
                )
            )
            return

        # Case 2: MethodView — app.add_url_rule("/path", view_func=UserAPI.as_view("name"))
        if (
            isinstance(view_func_node, ast.Call)
            and isinstance(view_func_node.func, ast.Attribute)
            and view_func_node.func.attr == "as_view"
        ):
            class_node = view_func_node.func.value
            class_name: str | None = None
            if isinstance(class_node, ast.Name):
                class_name = class_node.id
            elif isinstance(class_node, ast.Attribute):
                class_name = class_node.attr

            if class_name and class_name in self._method_view_classes:
                for verb, method_qualname in self._method_view_classes[class_name]:
                    self.routes.append(
                        RouteFact(
                            handler_name=method_qualname.rsplit(".", 1)[-1],
                            handler_qualname=method_qualname,
                            route_kind=RouteKind.METHOD_VIEW,
                            rule=rule,
                            methods=(verb,),
                            blueprint=None,
                            location=self._loc(node),
                            raw_code=_unparse_safe(node),
                            notes=(f"MethodView: {class_name}",),
                        )
                    )
            elif class_name:
                # Class not found in this file (or defined after the add_url_rule call).
                # Register with the provided methods as a best-effort fallback.
                self.routes.append(
                    RouteFact(
                        handler_name=class_name,
                        handler_qualname=self._resolve_local_name(class_name),
                        route_kind=RouteKind.METHOD_VIEW,
                        rule=rule,
                        methods=methods,
                        blueprint=None,
                        location=self._loc(node),
                        raw_code=_unparse_safe(node),
                        notes=(f"MethodView: {class_name} (unresolved)",),
                    )
                )

    def _check_add_resource(self, node: ast.Call) -> None:
        """Detect Flask-RESTX/RESTful ``api.add_resource(Resource, "/path")``."""
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "add_resource":
            return
        if not node.args:
            return

        class_node = node.args[0]
        class_qualname = self._resolve_class_reference(class_node)
        if class_qualname is None:
            return

        class_name = class_qualname.rsplit(".", 1)[-1]
        blueprint_name = (
            node.func.value.id if isinstance(node.func.value, ast.Name) else None
        )
        rules = [_str_literal(arg) for arg in node.args[1:]]
        rules = [rule for rule in rules if rule is not None]
        if not rules:
            rules = [None]

        for rule in rules:
            self._pending_resource_routes.append(
                _ResourceRouteRegistration(
                    class_name=class_name,
                    class_qualname=class_qualname,
                    rule=rule,
                    blueprint=blueprint_name,
                    location=self._loc(node),
                    raw_code=_unparse_safe(node),
                    notes=(
                        "framework:flask-restx-resource",
                        f"resource_class:{class_name}",
                        "registration:add_resource",
                    ),
                )
            )

    # --- Input access detection ---

    def visit_Call(self, node: ast.Call) -> None:
        # add_url_rule can appear at module scope or inside a function
        self._check_add_url_rule(node)
        self._check_add_resource(node)

        if self._current_function:
            self._check_input_access_call(node)
            self._check_get_json_call(node)
            self._check_function_call_edge(node)

        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self._current_function:
            self._check_input_access_subscript(node)

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self._current_function:
            source = self._resolve_input_source(node)
            if source is not None:
                self.input_accesses.append(
                    InputAccessFact(
                        function_qualname=self._current_function,
                        location=self._loc(node),
                        source=source,
                        accessor=AccessorKind.DIRECT,
                        key_expr=None,
                        key_literal=None,
                        raw_code=_unparse_safe(node),
                    )
                )
        self.generic_visit(node)

    def _resolve_input_source(self, node: ast.AST) -> InputSource | None:
        """Check if an AST node refers to a Flask request input source."""
        # request.args, request.form, etc. (handles import aliases like `req.args`)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in self._flask_request_names:
                source = _REQUEST_ATTR_SOURCE_MAP.get(node.attr)
                if source is not None:
                    return source

        # flask.request.args (triple attribute chain: module.request.attr)
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.attr == "request"
            and node.value.value.id in self._flask_module_aliases
        ):
            source = _REQUEST_ATTR_SOURCE_MAP.get(node.attr)
            if source is not None:
                return source

        # request.get_json() or alias.get_json() or flask.request.get_json()
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "get_json":
                receiver = node.func.value
                if isinstance(receiver, ast.Name) and receiver.id in self._flask_request_names:
                    return InputSource.JSON
                if (
                    isinstance(receiver, ast.Attribute)
                    and isinstance(receiver.value, ast.Name)
                    and receiver.attr == "request"
                    and receiver.value.id in self._flask_module_aliases
                ):
                    return InputSource.JSON

        # Local alias (e.g. `data = request.form; data.get(...)`)
        if isinstance(node, ast.Name) and node.id in self._request_aliases:
            return self._request_aliases[node.id]

        return None

    def _check_input_access_call(self, node: ast.Call) -> None:
        """Detect request.args.get("key"), request.form.getlist("key"), etc.

        Also detects accesses on function parameters (data.get("key")) for
        interprocedural source propagation.
        """
        if not isinstance(node.func, ast.Attribute):
            return

        accessor_name = node.func.attr
        if accessor_name not in {
            "get",
            "getlist",
            "get_json",
            "to_dict",
            "keys",
            "values",
            "items",
        }:
            return

        if accessor_name in {"get", "getlist"}:
            accessor = AccessorKind.GET if accessor_name == "get" else AccessorKind.GETLIST
            key_node = node.args[0] if node.args else None

            source = self._resolve_input_source(node.func.value)
            if source is not None:
                # Check for ternary alias — emit one fact per possible source
                ternary_sources = None
                if isinstance(node.func.value, ast.Name):
                    ternary_sources = self._ternary_aliases.get(node.func.value.id)

                sources_to_emit = ternary_sources if ternary_sources else [source]
                for src in sources_to_emit:
                    self.input_accesses.append(
                        InputAccessFact(
                            function_qualname=self._current_function,
                            location=self._loc(node),
                            source=src,
                            accessor=accessor,
                            key_expr=_unparse_safe(key_node) if key_node else None,
                            key_literal=_str_literal(key_node),
                            raw_code=_unparse_safe(node),
                        )
                    )
                return

            # Check if the receiver is a function parameter
            if isinstance(node.func.value, ast.Name) and self._current_function:
                param_name = node.func.value.id
                params = self._function_params.get(self._current_function, [])
                if param_name in params:
                    param_idx = params.index(param_name)
                    # Record as an unresolved parameter access
                    fact = InputAccessFact(
                        function_qualname=self._current_function,
                        location=self._loc(node),
                        source=InputSource.ARGS,  # placeholder, will be resolved
                        accessor=accessor,
                        key_expr=_unparse_safe(key_node) if key_node else None,
                        key_literal=_str_literal(key_node),
                        raw_code=_unparse_safe(node),
                        notes=("unresolved_param", f"param:{param_name}", f"param_idx:{param_idx}"),
                    )
                    self._param_accesses.append((self._current_function, param_idx, fact))

    def _check_get_json_call(self, node: ast.Call) -> None:
        """Detect request.get_json() calls (with any kwargs like silent=True)."""
        if not isinstance(node.func, ast.Attribute):
            return
        if node.func.attr != "get_json":
            return

        is_request = False
        # Direct: request.get_json() or alias.get_json()
        if (
            isinstance(node.func.value, ast.Name)
            and node.func.value.id in self._flask_request_names
            or (
                isinstance(node.func.value, ast.Attribute)
                and isinstance(node.func.value.value, ast.Name)
                and node.func.value.attr == "request"
                and node.func.value.value.id in self._flask_module_aliases
            )
        ):
            is_request = True

        if is_request:
            self.input_accesses.append(
                InputAccessFact(
                    function_qualname=self._current_function,
                    location=self._loc(node),
                    source=InputSource.JSON,
                    accessor=AccessorKind.DIRECT,
                    key_expr=None,
                    key_literal=None,
                    raw_code=_unparse_safe(node),
                )
            )

    def _check_input_access_subscript(self, node: ast.Subscript) -> None:
        """Detect request.args["key"], request.form["key"], etc."""
        source = self._resolve_input_source(node.value)
        key_node = node.slice

        if source is not None:
            self.input_accesses.append(
                InputAccessFact(
                    function_qualname=self._current_function,
                    location=self._loc(node),
                    source=source,
                    accessor=AccessorKind.INDEX,
                    key_expr=_unparse_safe(key_node) if key_node else None,
                    key_literal=_str_literal(key_node),
                    raw_code=_unparse_safe(node),
                )
            )
            return

        # Check if the receiver is a function parameter
        if isinstance(node.value, ast.Name) and self._current_function:
            param_name = node.value.id
            params = self._function_params.get(self._current_function, [])
            if param_name in params:
                param_idx = params.index(param_name)
                fact = InputAccessFact(
                    function_qualname=self._current_function,
                    location=self._loc(node),
                    source=InputSource.ARGS,  # placeholder
                    accessor=AccessorKind.INDEX,
                    key_expr=_unparse_safe(key_node) if key_node else None,
                    key_literal=_str_literal(key_node),
                    raw_code=_unparse_safe(node),
                    notes=("unresolved_param", f"param:{param_name}", f"param_idx:{param_idx}"),
                )
                self._param_accesses.append((self._current_function, param_idx, fact))

    # --- Call edge detection ---

    def _check_function_call_edge(self, node: ast.Call) -> None:
        callee_name: str | None = None

        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
            if callee_name in _COMMON_NON_PROJECT_CALLS:
                return
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in _DATA_ACCESSOR_METHODS:
                return
            callee_name = self._resolve_attribute_callee(node.func)

        if callee_name is None:
            return

        # Track what's being passed as arguments
        arg_map: dict[int, str] = {}
        current_params = self._function_params.get(self._current_function, [])

        for i, arg in enumerate(node.args):
            code = _unparse_safe(arg)
            if self._is_request_related(code):
                arg_map[i] = code
            # Track parameter forwarding: when this function passes its own
            # parameter as an argument to another function (for multi-level propagation).
            elif isinstance(arg, ast.Name) and arg.id in current_params:
                caller_param_idx = current_params.index(arg.id)
                self._param_forwarding.append(
                    (self._current_function, caller_param_idx, callee_name, i)
                )

        for kw in node.keywords:
            if kw.arg and self._is_request_related(_unparse_safe(kw.value)):
                arg_map[-1] = f"{kw.arg}={_unparse_safe(kw.value)}"

        self.call_edges.append(
            CallEdge(
                caller_qualname=self._current_function,
                callee_qualname=callee_name,
                location=self._loc(node),
                argument_map=arg_map if arg_map else None,
            )
        )

    def _resolve_attribute_callee(self, func: ast.Attribute) -> str | None:
        """Resolve method calls that are local enough to model safely.

        Attribute calls such as ``data.get(...)`` and ``client.get(...)`` are
        not reliable project call edges without type information.  For class
        methods, however, ``self._process_args()`` and ``Base._process_args(self)``
        carry enough local structure to emit class-qualified edges.
        """
        receiver = func.value
        if isinstance(receiver, ast.Name):
            if receiver.id in {"self", "cls"} and self._current_class:
                return f"{self.module}.{self._current_class}.{func.attr}"
            if receiver.id in self._class_qualnames:
                return f"{self._class_qualnames[receiver.id]}.{func.attr}"
            if receiver.id in self._import_aliases:
                return f"{self._import_aliases[receiver.id]}.{func.attr}"
        return None

    def _is_request_related(self, code: str) -> bool:
        suffixes = [
            ".args",
            ".form",
            ".values",
            ".json",
            ".get_json",
            ".data",
            ".headers",
            ".cookies",
            ".files",
        ]
        for name in self._flask_request_names:
            for suffix in suffixes:
                if name + suffix in code:
                    return True
        # Also match flask.request.X patterns
        for mod in self._flask_module_aliases:
            for suffix in suffixes:
                if f"{mod}.request{suffix}" in code:
                    return True
        return False

    # --- Dict merge detection ---

    def visit_Dict(self, node: ast.Dict) -> None:
        if self._current_function and any(key is None for key in node.keys):
            # Dict with ** unpacking
            sources = []
            for key, value in zip(node.keys, node.values):
                if key is None:
                    sources.append(_unparse_safe(value))
            if len(sources) >= 2:
                self.dict_merges.append(
                    DictMergeFact(
                        function_qualname=self._current_function,
                        location=self._loc(node),
                        sources=tuple(sources),
                        raw_code=_unparse_safe(node),
                    )
                )

        self.generic_visit(node)

    # --- Handle inline request source detection for ternary/or patterns ---

    def visit_IfExp(self, node: ast.IfExp) -> None:
        """Detect patterns like: request.json if request.is_json else request.form"""
        if self._current_function:
            body_src = self._resolve_input_source(node.body)
            else_src = self._resolve_input_source(node.orelse)
            if body_src is not None or else_src is not None:
                # The assignment target will be caught by visit_Assign
                pass
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


class ASTBackend:
    """Pure Python AST-based code analysis backend."""

    name = "ast"

    def extract(self, target: Path) -> ExtractionResult:
        target = Path(target).resolve()
        if target.is_file():
            files = [target]
            project_root = str(target.parent)
        else:
            files = sorted(target.rglob("*.py"))
            project_root = str(target)

        all_routes: list[RouteFact] = []
        all_accesses: list[InputAccessFact] = []
        all_edges: list[CallEdge] = []
        all_before: list[BeforeRequestFact] = []
        all_merges: list[DictMergeFact] = []
        all_param_accesses: list[tuple[str, int, InputAccessFact]] = []
        all_function_params: dict[str, list[str]] = {}
        all_param_forwarding: list[tuple[str, int, str, int]] = []
        all_request_names: set[str] = {"request"}
        all_flask_module_aliases: set[str] = {"flask"}
        all_class_methods: dict[str, set[str]] = {}
        all_class_bases: dict[str, tuple[str, ...]] = {}
        all_pending_resource_routes: list[_ResourceRouteRegistration] = []

        for f in files:
            try:
                source = f.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(f))
            except (SyntaxError, UnicodeDecodeError):
                continue

            module_name = _module_qualname(str(f), project_root)
            visitor = _FileVisitor(str(f), module_name)
            visitor.visit(tree)

            all_routes.extend(visitor.routes)
            all_accesses.extend(visitor.input_accesses)
            all_edges.extend(visitor.call_edges)
            all_before.extend(visitor.before_requests)
            all_merges.extend(visitor.dict_merges)
            all_param_accesses.extend(visitor._param_accesses)
            all_function_params.update(visitor._function_params)
            all_param_forwarding.extend(visitor._param_forwarding)
            all_request_names.update(visitor._flask_request_names)
            all_flask_module_aliases.update(visitor._flask_module_aliases)
            all_pending_resource_routes.extend(visitor._pending_resource_routes)
            for class_qualname, methods in visitor._class_methods.items():
                all_class_methods.setdefault(class_qualname, set()).update(methods)
            all_class_bases.update(visitor._class_bases)

        all_routes.extend(
            self._resource_route_facts(all_pending_resource_routes, all_class_methods)
        )

        # Resolve call edge qualnames
        all_edges = self._resolve_call_edges(
            all_edges, all_routes, all_accesses, all_function_params
        )
        all_edges.extend(
            self._class_handler_lifecycle_edges(
                all_routes,
                all_class_methods,
                all_class_bases,
            )
        )

        # Propagate sources through function parameters (iterative for multi-level)
        propagated = self._propagate_sources(
            all_edges,
            all_param_accesses,
            all_function_params,
            all_param_forwarding,
            all_request_names,
            all_flask_module_aliases,
        )
        all_accesses.extend(propagated)

        return ExtractionResult(
            routes=all_routes,
            input_accesses=all_accesses,
            call_edges=all_edges,
            before_requests=all_before,
            dict_merges=all_merges,
        )

    def _resource_route_facts(
        self,
        registrations: list[_ResourceRouteRegistration],
        class_methods: dict[str, set[str]],
    ) -> list[RouteFact]:
        """Resolve deferred ``add_resource`` registrations to method endpoints."""
        routes: list[RouteFact] = []
        seen: set[tuple[str, str | None, str, str]] = set()

        for registration in registrations:
            methods = class_methods.get(registration.class_qualname, set())
            if not methods:
                continue

            for method_name in _HTTP_VERB_METHODS:
                method_qualname = f"{registration.class_qualname}.{method_name}"
                if method_qualname not in methods:
                    continue

                verb = method_name.upper()
                key = (
                    registration.class_qualname,
                    registration.rule,
                    method_qualname,
                    verb,
                )
                if key in seen:
                    continue
                seen.add(key)

                routes.append(
                    RouteFact(
                        handler_name=method_name,
                        handler_qualname=method_qualname,
                        route_kind=RouteKind.ENDPOINT,
                        rule=registration.rule,
                        methods=(verb,),
                        blueprint=registration.blueprint,
                        location=registration.location,
                        raw_code=registration.raw_code,
                        notes=registration.notes,
                    )
                )

        return routes

    def _class_handler_lifecycle_edges(
        self,
        routes: list[RouteFact],
        class_methods: dict[str, set[str]],
        class_bases: dict[str, tuple[str, ...]],
    ) -> list[CallEdge]:
        """Add conservative endpoint-context edges for Flask class handlers.

        Frameworks such as Indico register handler classes instead of plain
        functions.  The request-relevant work then lives in lifecycle methods
        like ``_process_args`` and ``_process``.  We connect the route class
        pseudo-node directly to the resolved implementation for each known
        lifecycle method.  This keeps endpoint reachability class-scoped and
        avoids making shared base methods reach every subclass override.
        """
        edges: list[CallEdge] = []
        seen: set[tuple[str, str, str, int]] = set()

        for route in routes:
            class_qualname = route.handler_qualname
            if class_qualname not in class_methods and class_qualname not in class_bases:
                continue

            for method_name in _CLASS_HANDLER_LIFECYCLE_METHODS:
                implementation = self._resolve_class_method(
                    class_qualname,
                    method_name,
                    class_methods,
                    class_bases,
                )
                if implementation is None:
                    continue
                key = (class_qualname, implementation, route.location.file, route.location.line)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    CallEdge(
                        caller_qualname=class_qualname,
                        callee_qualname=implementation,
                        location=route.location,
                        argument_map=None,
                    )
                )

        return edges

    def _resolve_class_method(
        self,
        class_qualname: str,
        method_name: str,
        class_methods: dict[str, set[str]],
        class_bases: dict[str, tuple[str, ...]],
        seen: set[str] | None = None,
    ) -> str | None:
        """Resolve ``method_name`` on ``class_qualname`` using local class metadata."""
        seen = seen or set()
        if class_qualname in seen:
            return None
        seen.add(class_qualname)

        candidate = f"{class_qualname}.{method_name}"
        if candidate in class_methods.get(class_qualname, set()):
            return candidate

        for base_qualname in class_bases.get(class_qualname, ()):
            resolved = self._resolve_class_method(
                base_qualname,
                method_name,
                class_methods,
                class_bases,
                seen,
            )
            if resolved is not None:
                return resolved

        return None

    def _resolve_call_edges(
        self,
        edges: list[CallEdge],
        routes: list[RouteFact],
        accesses: list[InputAccessFact],
        function_params: dict[str, list[str]],
    ) -> list[CallEdge]:
        """Try to resolve short callee names to full qualnames using known functions."""
        known_functions: dict[str, list[str]] = {}
        for r in routes:
            short = r.handler_name
            known_functions.setdefault(short, []).append(r.handler_qualname)
        for a in accesses:
            parts = a.function_qualname.rsplit(".", 1)
            if len(parts) == 2:
                short = parts[1]
                known_functions.setdefault(short, []).append(a.function_qualname)
        for qualname in function_params:
            parts = qualname.rsplit(".", 1)
            if len(parts) == 2:
                short = parts[1]
                known_functions.setdefault(short, []).append(qualname)

        resolved: list[CallEdge] = []
        for edge in edges:
            callee = edge.callee_qualname
            if "." not in callee and callee in known_functions:
                caller_module = (
                    edge.caller_qualname.rsplit(".", 1)[0] if "." in edge.caller_qualname else ""
                )
                candidates = known_functions[callee]
                # Prefer same-module candidate
                same_module = [c for c in candidates if c.rsplit(".", 1)[0] == caller_module]
                if not same_module:
                    # Try prefix match (for cross-module calls within same package)
                    pkg = caller_module.rsplit(".", 1)[0] if "." in caller_module else caller_module
                    same_module = [c for c in candidates if c.startswith(pkg + ".")]
                if same_module:
                    callee = same_module[0]
                elif len(candidates) == 1:
                    callee = candidates[0]

            resolved.append(
                CallEdge(
                    caller_qualname=edge.caller_qualname,
                    callee_qualname=callee,
                    location=edge.location,
                    argument_map=edge.argument_map,
                )
            )

        return resolved

    def _propagate_sources(
        self,
        edges: list[CallEdge],
        param_accesses: list[tuple[str, int, InputAccessFact]],
        function_params: dict[str, list[str]],
        param_forwarding: list[tuple[str, int, str, int]] | None = None,
        request_names: set[str] | None = None,
        flask_module_aliases: set[str] | None = None,
    ) -> list[InputAccessFact]:
        """Resolve unresolved parameter accesses using call edge argument maps.

        When a function is called with request.form as an argument, all
        parameter accesses in that function on that parameter get resolved
        to InputSource.FORM.

        Multi-level: if function B receives request.form as param 0 and
        forwards it (as its own parameter) to function C's param 0, then
        C's param 0 also resolves to FORM. Iterates until convergence.
        """
        param_forwarding = param_forwarding or []
        request_names = request_names or {"request"}
        flask_module_aliases = flask_module_aliases or {"flask"}

        # Build callee short name -> resolved qualname mapping
        known_qualnames: dict[str, list[str]] = {}
        for qualname in function_params:
            short = qualname.rsplit(".", 1)[-1]
            known_qualnames.setdefault(short, []).append(qualname)

        # Resolve forwarding callee short names to qualnames
        resolved_forwarding: list[tuple[str, int, str, int]] = []
        for caller_qn, caller_pidx, callee_short, callee_aidx in param_forwarding:
            candidates = known_qualnames.get(callee_short, [])
            # Prefer same-module candidate
            caller_mod = caller_qn.rsplit(".", 1)[0] if "." in caller_qn else ""
            same_mod = [c for c in candidates if c.rsplit(".", 1)[0] == caller_mod]
            if same_mod:
                resolved_forwarding.append((caller_qn, caller_pidx, same_mod[0], callee_aidx))
            elif len(candidates) == 1:
                resolved_forwarding.append((caller_qn, caller_pidx, candidates[0], callee_aidx))

        # Map: (callee_qualname, param_idx) -> set of InputSources from callers
        param_sources: dict[tuple[str, int], set[InputSource]] = {}

        # Pass 1: Resolve from direct call edges (argument_map contains request.X code)
        for edge in edges:
            if not edge.argument_map:
                continue
            for arg_idx, arg_code in edge.argument_map.items():
                if arg_idx < 0:
                    continue
                source = _code_to_input_source(arg_code, request_names, flask_module_aliases)
                if source is not None:
                    param_sources.setdefault((edge.callee_qualname, arg_idx), set()).add(source)

        # Iterative passes: propagate through parameter forwarding chains
        max_iterations = 5
        for _ in range(max_iterations):
            new_entries = False
            for caller_qn, caller_pidx, callee_qn, callee_aidx in resolved_forwarding:
                # If the caller's param has been resolved to a source, propagate it
                caller_sources = param_sources.get((caller_qn, caller_pidx), set())
                if not caller_sources:
                    continue
                key = (callee_qn, callee_aidx)
                existing = param_sources.get(key, set())
                added = caller_sources - existing
                if added:
                    param_sources.setdefault(key, set()).update(added)
                    new_entries = True
            if not new_entries:
                break

        # Resolve each parameter access
        resolved: list[InputAccessFact] = []
        for func_qualname, param_idx, fact in param_accesses:
            sources = param_sources.get((func_qualname, param_idx), set())
            for source in sorted(sources, key=lambda s: s.value):
                resolved.append(
                    InputAccessFact(
                        function_qualname=fact.function_qualname,
                        location=fact.location,
                        source=source,
                        accessor=fact.accessor,
                        key_expr=fact.key_expr,
                        key_literal=fact.key_literal,
                        raw_code=fact.raw_code,
                        notes=(f"propagated from caller via {source.value}",),
                    )
                )

        return resolved


def _code_to_input_source(
    code: str,
    request_names: set[str] | None = None,
    flask_module_aliases: set[str] | None = None,
) -> InputSource | None:
    """Convert a source code string to an InputSource."""
    code = code.strip()
    names = request_names or {"request"}
    modules = flask_module_aliases or {"flask"}

    attr_sources = [
        (".args", InputSource.ARGS),
        (".form", InputSource.FORM),
        (".values", InputSource.VALUES),
        (".json", InputSource.JSON),
        (".get_json", InputSource.JSON),
        (".data", InputSource.DATA),
        (".headers", InputSource.HEADERS),
        (".cookies", InputSource.COOKIES),
        (".files", InputSource.FILES),
    ]

    # Check direct request name aliases (e.g. req.form)
    for name in names:
        for suffix, source in attr_sources:
            if name + suffix in code:
                return source
    # Check module-qualified aliases (e.g. fl.request.form)
    for mod in modules:
        for suffix, source in attr_sources:
            if f"{mod}.request{suffix}" in code:
                return source
    return None
