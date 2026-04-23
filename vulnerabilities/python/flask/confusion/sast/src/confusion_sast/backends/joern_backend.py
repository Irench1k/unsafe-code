"""Joern-based code analysis backend.

Uses Joern's CPG (Code Property Graph) via CLI for interprocedural
dataflow analysis. Requires `joern` and `joern-parse` CLI tools.

This backend adds value beyond the AST backend for:
- Cross-file/cross-module dataflow via Joern's dataflow engine
- Taint tracking through complex call chains
- Dataflow witnesses (source-to-sink paths)

Note: Joern's Python frontend does NOT model decorators as annotations.
Route detection uses code-pattern matching on call nodes instead.
Decorators are lowered to call-of-call patterns like:
  bp.route("/path", methods=["POST"])(def handler_name(...))
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from ..models import (
    AccessorKind,
    BeforeRequestFact,
    CallEdge,
    InputAccessFact,
    InputSource,
    Location,
    RouteFact,
    RouteKind,
)
from .augment import augment_with_ast
from .interface import ExtractionResult

# ---------------------------------------------------------------------------
# Scala query script template
# ---------------------------------------------------------------------------

# Uses string interpolation for clean JSON output (avoids broken Map.toJsonPretty).
# Sentinel lines delimit sections so the parser can split stdout reliably.
_SCALA_SCRIPT = r'''
importCode("{target_path}", "pythonsrc")

// -----------------------------------------------------------------------
// Routes: decorator application calls  bp.route(...)(def handler(...))
// These have name="" and contain both the route info and handler name.
// -----------------------------------------------------------------------
println("===ROUTES===")
cpg.call.filter(c =>
  c.method.fullName.endsWith(":<module>") &&
  c.name == "" &&
  c.code.matches(".*\\.(route|get|post|put|patch|delete)\\(.*\\)\\(.*def .*\\)")
).foreach { c =>
  val code = c.code.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "")
  val file = c.file.name.headOption.getOrElse("")
  val line = c.lineNumber.getOrElse(-1)
  println(s"""JSONL:{"code":"$code","file":"$file","line":$line}""")
}

// -----------------------------------------------------------------------
// Input accesses: direct request.* field accesses
// -----------------------------------------------------------------------
println("===ACCESSES===")
cpg.call.filter(c =>
  c.name == "<operator>.fieldAccess" &&
  c.code.matches("request\\.(args|form|values|json|data|headers|cookies|files)")
).foreach { c =>
  val code = c.code.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "")
  val method = c.method.fullName.replace("\\", "\\\\").replace("\"", "\\\"")
  val file = c.file.name.headOption.getOrElse("")
  val line = c.lineNumber.getOrElse(-1)
  println(s"""JSONL:{"code":"$code","method":"$method","file":"$file","line":$line,"kind":"direct"}""")
}

// request.get_json() calls
cpg.call.filter(c =>
  c.name == "get_json" &&
  c.code.contains("request.get_json")
).foreach { c =>
  val code = c.code.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "")
  val method = c.method.fullName.replace("\\", "\\\\").replace("\"", "\\\"")
  val file = c.file.name.headOption.getOrElse("")
  val line = c.lineNumber.getOrElse(-1)
  println(s"""JSONL:{"code":"$code","method":"$method","file":"$file","line":$line,"kind":"get_json"}""")
}

// .get("key") and .getlist("key") calls on request sources only
// Only matches request.args.get(...), request.form.getlist(...), etc.
// Parametric accesses (data.get("key")) are left to AST augmentation.
cpg.call.filter(c =>
  (c.name == "get" || c.name == "getlist") &&
  c.code.matches("request\\.(args|form|values|json|data|headers|cookies|files)\\.(get|getlist)\\(.*\\)")
).foreach { c =>
  val code = c.code.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "")
  val method = c.method.fullName.replace("\\", "\\\\").replace("\"", "\\\"")
  val file = c.file.name.headOption.getOrElse("")
  val line = c.lineNumber.getOrElse(-1)
  println(s"""JSONL:{"code":"$code","method":"$method","file":"$file","line":$line,"kind":"accessor"}""")
}

// -----------------------------------------------------------------------
// Call edges: caller -> callee for project functions
// -----------------------------------------------------------------------
println("===CALLEDGES===")
cpg.method.filter(m =>
  m.filename.endsWith(".py")
).foreach { m =>
  val caller = m.fullName.replace("\\", "\\\\").replace("\"", "\\\"")
  val callerFile = m.filename.replace("\\", "\\\\").replace("\"", "\\\"")
  val callerLine = m.lineNumber.getOrElse(-1)
  m.callee.filter(c =>
    c.fullName.contains(".py:<module>.") &&
    !c.fullName.startsWith("<operator>")
  ).dedup.foreach { c =>
    val callee = c.fullName.replace("\\", "\\\\").replace("\"", "\\\"")
    println(s"""JSONL:{"caller":"$caller","callee":"$callee","file":"$callerFile","line":$callerLine}""")
  }
}

// -----------------------------------------------------------------------
// Before-request hooks: bp.before_request(def middleware_func(...))
// Same call-of-call pattern as routes.
// -----------------------------------------------------------------------
println("===BEFOREREQS===")
cpg.call.filter(c =>
  c.method.fullName.endsWith(":<module>") &&
  c.name == "" &&
  c.code.matches(".*\\.before_request\\(.*def .*\\)")
).foreach { c =>
  val code = c.code.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "")
  val file = c.file.name.headOption.getOrElse("")
  val line = c.lineNumber.getOrElse(-1)
  println(s"""JSONL:{"code":"$code","file":"$file","line":$line}""")
}
'''


# ---------------------------------------------------------------------------
# Qualname normalization
# ---------------------------------------------------------------------------


def _normalize_qualname(joern_fullname: str) -> str:
    """Transform Joern fullName to dotted module qualname.

    Joern:  routes.py:<module>.create_new_order
    Output: routes.create_new_order

    Joern:  subdir/routes.py:<module>.MyClass.method
    Output: subdir.routes.MyClass.method
    """
    if ":<module>." in joern_fullname:
        file_part, func_part = joern_fullname.split(":<module>.", 1)
        module = file_part.removesuffix(".py").replace("/", ".")
        if module.endswith(".__init__"):
            module = module.removesuffix(".__init__")
        elif module == "__init__":
            module = ""
        return f"{module}.{func_part}" if module else func_part
    if ":<module>" in joern_fullname:
        # Module-level (no function suffix)
        file_part = joern_fullname.split(":<module>", 1)[0]
        module = file_part.removesuffix(".py").replace("/", ".")
        if module.endswith(".__init__"):
            module = module.removesuffix(".__init__")
        elif module == "__init__":
            module = ""
        return module
    return joern_fullname


# ---------------------------------------------------------------------------
# Code pattern extractors (run on the Python code strings Joern captures)
# ---------------------------------------------------------------------------

_RE_HANDLER_NAME = re.compile(r"def\s+(\w+)")
_RE_ROUTE_RULE = re.compile(r"""['"](/[^'"]*?)['"]""")
_RE_METHODS_KEYWORD = re.compile(r"""methods\s*=\s*\[([^\]]*)\]""")
_RE_STRING_LITERAL = re.compile(r"""['"]([^'"]+)['"]""")
_RE_GET_KEY = re.compile(r"""\.(get|getlist)\(\s*['"]([^'"]+)['"]""")
_RE_SHORTHAND = re.compile(r"""\.(get|post|put|patch|delete)\(""")


def _extract_handler_name(code: str) -> str:
    """Extract handler function name from decorator application code."""
    m = _RE_HANDLER_NAME.search(code)
    return m.group(1) if m else "<unknown>"


def _extract_route_rule(code: str) -> str | None:
    """Extract URL rule from route decorator code."""
    m = _RE_ROUTE_RULE.search(code)
    return m.group(1) if m else None


def _extract_methods(code: str) -> tuple[str, ...]:
    """Extract HTTP methods from route decorator code."""
    # Check shorthand decorators first: .get(...), .post(...), etc.
    m = _RE_SHORTHAND.search(code)
    if m and ".route(" not in code:
        return (m.group(1).upper(),)

    # Look for methods=[...] keyword
    m = _RE_METHODS_KEYWORD.search(code)
    if m:
        inner = m.group(1)
        methods = _RE_STRING_LITERAL.findall(inner)
        if methods:
            return tuple(sorted(set(s.upper() for s in methods)))

    return ("GET",)


def _extract_blueprint(code: str) -> str | None:
    """Extract blueprint variable name from decorator code."""
    m = re.match(r"(\w+)\.", code)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Input source / accessor inference
# ---------------------------------------------------------------------------


def _infer_source(code: str) -> InputSource | None:
    """Infer the InputSource from access code."""
    if "request.args" in code:
        return InputSource.ARGS
    if "request.form" in code:
        return InputSource.FORM
    if "request.values" in code:
        return InputSource.VALUES
    if "request.json" in code or "request.get_json" in code:
        return InputSource.JSON
    if "request.data" in code:
        return InputSource.DATA
    if "request.headers" in code:
        return InputSource.HEADERS
    if "request.cookies" in code:
        return InputSource.COOKIES
    if "request.files" in code:
        return InputSource.FILES
    return None


def _infer_accessor_and_key(code: str) -> tuple[AccessorKind, str | None]:
    """Infer accessor kind and key from access code."""
    m = _RE_GET_KEY.search(code)
    if m:
        kind_str, key = m.group(1), m.group(2)
        accessor = AccessorKind.GETLIST if kind_str == "getlist" else AccessorKind.GET
        return accessor, key

    # .get() or .getlist() with a variable/expression argument (no string literal)
    m = re.search(r"\.(get|getlist)\(", code)
    if m:
        accessor = AccessorKind.GETLIST if m.group(1) == "getlist" else AccessorKind.GET
        return accessor, None

    # Subscript: ["key"]
    m = re.search(r"""\[\s*['"](\w+)['"]\s*\]""", code)
    if m:
        return AccessorKind.INDEX, m.group(1)

    return AccessorKind.DIRECT, None


# ---------------------------------------------------------------------------
# File path resolution
# ---------------------------------------------------------------------------


def _resolve_file(target: Path, bare_filename: str) -> str:
    """Resolve a bare filename from Joern to a full path.

    Joern stores just the filename (e.g., 'routes.py'). We resolve it
    against the target directory to get a full path matching what the
    AST backend produces.
    """
    if not bare_filename or bare_filename == "<empty>":
        return ""
    candidate = target / bare_filename
    if candidate.exists():
        return str(candidate)
    # Try recursive search for subdirectories
    matches = list(target.rglob(bare_filename))
    if matches:
        return str(matches[0])
    return bare_filename


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


class JoernBackend:
    """Joern CPG-based code analysis backend.

    Uses a single ``joern --script`` invocation that generates the CPG
    and runs all extraction queries, avoiding multiple JVM startups.

    All temporary files (CPG, workspace, script) are created in a
    ``tempfile.TemporaryDirectory`` and cleaned up after extraction.
    """

    name = "joern"

    def __init__(
        self,
        joern_path: str = "joern",
        parse_path: str = "joern-parse",
        debug: bool = False,
    ) -> None:
        self._joern = joern_path
        self._parse = parse_path
        self._debug = debug

    def extract(self, target: Path) -> ExtractionResult:
        target = Path(target).resolve()

        with tempfile.TemporaryDirectory(prefix="joern_sast_") as tmpdir:
            stdout = self._run_combined_script(target, Path(tmpdir))

        sections = self._split_sections(stdout)
        routes = self._parse_routes(sections.get("ROUTES", ""), target)
        accesses = self._parse_accesses(sections.get("ACCESSES", ""), target)
        edges = self._parse_call_edges(sections.get("CALLEDGES", ""), target)
        before_requests = self._parse_before_requests(
            sections.get("BEFOREREQS", ""),
            target,
        )

        result = ExtractionResult(
            routes=routes,
            input_accesses=accesses,
            call_edges=edges,
            before_requests=before_requests,
            dict_merges=[],
        )

        # Fill gaps with AST analysis (aliases, parameter propagation,
        # dict merges, and any accesses on aliased variables).
        # Routes are already perfect from Joern — skip re-filling them.
        return augment_with_ast(result, target, fill_routes=False)

    # --- Script execution ---

    def _run_combined_script(self, target: Path, workdir: Path) -> str:
        """Generate CPG and run all queries in a single JVM invocation."""
        # Build Scala script with target path interpolated
        escaped_target = str(target).replace("\\", "\\\\").replace('"', '\\"')
        script_content = _SCALA_SCRIPT.replace("{target_path}", escaped_target)

        script_path = workdir / "extract.sc"
        script_path.write_text(script_content)

        if self._debug:
            print(f"[joern] workdir: {workdir}", file=sys.stderr)
            print(f"[joern] target:  {target}", file=sys.stderr)
            print(f"[joern] script:  {script_path}", file=sys.stderr)

        result = subprocess.run(
            [self._joern, "--script", str(script_path)],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(workdir),
        )

        if self._debug:
            if result.stderr:
                print(f"[joern] stderr:\n{result.stderr}", file=sys.stderr)
            print(f"[joern] return code: {result.returncode}", file=sys.stderr)

        if result.returncode != 0:
            raise RuntimeError(
                f"joern --script failed (rc={result.returncode}):\n{result.stderr[-2000:]}"
            )

        return result.stdout

    # --- Output parsing ---

    @staticmethod
    def _split_sections(stdout: str) -> dict[str, str]:
        """Split sentinel-delimited output into named sections."""
        sections: dict[str, str] = {}
        current_name: str | None = None
        current_lines: list[str] = []

        for line in stdout.splitlines():
            stripped = line.strip()
            m = re.match(r"^===(\w+)===$", stripped)
            if m:
                if current_name is not None:
                    sections[current_name] = "\n".join(current_lines)
                current_name = m.group(1)
                current_lines = []
            elif current_name is not None:
                current_lines.append(line)

        if current_name is not None:
            sections[current_name] = "\n".join(current_lines)

        return sections

    def _parse_json_lines(self, text: str) -> list[dict]:
        """Parse JSONL: prefixed lines from Joern output.

        Each JSON record is emitted by the Scala script as ``JSONL:{...}``.
        The prefix ensures we skip Joern's log noise without guessing.
        """
        prefix = "JSONL:"
        results = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith(prefix):
                continue
            payload = line[len(prefix) :]
            try:
                results.append(json.loads(payload))
            except json.JSONDecodeError:
                if self._debug:
                    print(f"[joern] bad JSON line: {payload!r}", file=sys.stderr)
        return results

    # --- Route parsing ---

    def _parse_routes(self, text: str, target: Path) -> list[RouteFact]:
        rows = self._parse_json_lines(text)
        results: list[RouteFact] = []

        for row in rows:
            code = row.get("code", "")
            handler_name = _extract_handler_name(code)
            if handler_name == "<unknown>":
                continue

            # Build qualname from file: routes.py -> routes.handler_name
            bare_file = row.get("file", "")
            module = bare_file.removesuffix(".py").replace("/", ".")
            if module.endswith(".__init__"):
                module = module.removesuffix(".__init__")
            elif module == "__init__":
                module = ""
            handler_qualname = f"{module}.{handler_name}" if module else handler_name

            results.append(
                RouteFact(
                    handler_name=handler_name,
                    handler_qualname=handler_qualname,
                    route_kind=RouteKind.DECORATOR,
                    rule=_extract_route_rule(code),
                    methods=_extract_methods(code),
                    blueprint=_extract_blueprint(code),
                    location=Location(
                        file=_resolve_file(target, bare_file),
                        line=int(row.get("line", 0)),
                    ),
                    raw_code=code,
                )
            )

        return results

    # --- Input access parsing ---

    def _parse_accesses(self, text: str, target: Path) -> list[InputAccessFact]:
        rows = self._parse_json_lines(text)
        results: list[InputAccessFact] = []

        for row in rows:
            code = row.get("code", "")
            kind = row.get("kind", "")
            method = row.get("method", "")
            func_qualname = _normalize_qualname(method)
            bare_file = row.get("file", "")
            loc = Location(
                file=_resolve_file(target, bare_file),
                line=int(row.get("line", 0)),
            )

            if kind == "direct":
                source = _infer_source(code)
                if source is None:
                    continue
                results.append(
                    InputAccessFact(
                        function_qualname=func_qualname,
                        location=loc,
                        source=source,
                        accessor=AccessorKind.DIRECT,
                        key_expr=None,
                        key_literal=None,
                        raw_code=code,
                    )
                )

            elif kind == "get_json":
                results.append(
                    InputAccessFact(
                        function_qualname=func_qualname,
                        location=loc,
                        source=InputSource.JSON,
                        accessor=AccessorKind.DIRECT,
                        key_expr=None,
                        key_literal=None,
                        raw_code=code,
                    )
                )

            elif kind == "accessor":
                accessor, key = _infer_accessor_and_key(code)
                source = _infer_source(code)
                if source is None:
                    # Narrowed Scala query should prevent this, but skip
                    # any unresolved accesses — augment_with_ast fills gaps.
                    continue

                results.append(
                    InputAccessFact(
                        function_qualname=func_qualname,
                        location=loc,
                        source=source,
                        accessor=accessor,
                        key_expr=key,
                        key_literal=key,
                        raw_code=code,
                    )
                )

        return results

    # --- Call edge parsing ---

    # Joern emits spurious call edges when it can't resolve parameter types.
    # For example, data.get() on an untyped parameter produces edges to
    # flask.request.headers.get, os.environ.get, etc.
    _SPURIOUS_CALLEE_FRAGMENTS = (
        "flask.request.",
        "os.<member>",
        "os.environ",
    )

    def _parse_call_edges(self, text: str, target: Path) -> list[CallEdge]:
        rows = self._parse_json_lines(text)
        results: list[CallEdge] = []
        seen: set[tuple[str, str]] = set()

        for row in rows:
            raw_callee = row.get("callee", "")
            caller = _normalize_qualname(row.get("caller", ""))
            callee = _normalize_qualname(raw_callee)
            bare_file = row.get("file", "")

            # Skip self-loops and duplicate edges
            if caller == callee:
                continue
            edge_key = (caller, callee)
            if edge_key in seen:
                continue
            seen.add(edge_key)

            # Skip edges involving module-level or built-in scopes
            if caller.endswith(".<module>") or callee.endswith(".<module>"):
                continue

            # Skip spurious edges from Joern's type-confused resolution
            if any(frag in raw_callee for frag in self._SPURIOUS_CALLEE_FRAGMENTS):
                continue

            results.append(
                CallEdge(
                    caller_qualname=caller,
                    callee_qualname=callee,
                    location=Location(
                        file=_resolve_file(target, bare_file),
                        line=int(row.get("line", 0)),
                    ),
                )
            )

        return results

    # --- Before-request parsing ---

    def _parse_before_requests(
        self,
        text: str,
        target: Path,
    ) -> list[BeforeRequestFact]:
        rows = self._parse_json_lines(text)
        results: list[BeforeRequestFact] = []

        for row in rows:
            code = row.get("code", "")
            handler_name = _extract_handler_name(code)
            if handler_name == "<unknown>":
                continue

            bare_file = row.get("file", "")
            module = bare_file.removesuffix(".py").replace("/", ".")
            func_qualname = f"{module}.{handler_name}" if module else handler_name

            blueprint = _extract_blueprint(code)

            results.append(
                BeforeRequestFact(
                    function_qualname=func_qualname,
                    blueprint=blueprint,
                    location=Location(
                        file=_resolve_file(target, bare_file),
                        line=int(row.get("line", 0)),
                    ),
                )
            )

        return results
