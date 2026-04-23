"""Domain models for confusion SAST.

These are the normalized facts that all backends produce and all detection
rules consume. The detection engine never imports from a backend module --
it operates exclusively over these facts and a NetworkX graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InputSource(Enum):
    """Where a Flask request input originates."""

    ARGS = "args"  # request.args  (query string)
    FORM = "form"  # request.form  (form-encoded body)
    VALUES = "values"  # request.values (merged args + form)
    JSON = "json"  # request.json / request.get_json()
    DATA = "data"  # request.data  (raw body bytes)
    HEADERS = "headers"  # request.headers
    COOKIES = "cookies"  # request.cookies
    FILES = "files"  # request.files

    def __repr__(self) -> str:
        return f"InputSource.{self.name}"


class AccessorKind(Enum):
    """How a value is retrieved from an input source."""

    GET = "get"  # .get(key)
    GETLIST = "getlist"  # .getlist(key)
    INDEX = "index"  # [key]  (subscript)
    ATTR = "attr"  # .key   (attribute access)
    DIRECT = "direct"  # the source object passed as-is (e.g. request.form passed to a function)

    def __repr__(self) -> str:
        return f"AccessorKind.{self.name}"


class RouteKind(Enum):
    """How a route was registered."""

    DECORATOR = "decorator"
    ADD_URL_RULE = "add_url_rule"
    ENDPOINT = "endpoint"
    METHOD_VIEW = "method_view"

    def __repr__(self) -> str:
        return f"RouteKind.{self.name}"


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Location:
    """Source location for a fact."""

    file: str
    line: int
    col: int = 0

    def __str__(self) -> str:
        return f"{self.file}:{self.line}"


# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RouteFact:
    """A discovered route/endpoint registration."""

    handler_name: str  # function name (e.g. "create_new_order")
    handler_qualname: str  # fully qualified (e.g. "webapp.r01...e01.routes.create_new_order")
    route_kind: RouteKind
    rule: str | None  # URL pattern (e.g. "/orders")
    methods: tuple[str, ...]  # HTTP methods (e.g. ("POST",))
    blueprint: str | None  # blueprint name if applicable
    location: Location
    raw_code: str  # the decorator/call text
    notes: tuple[str, ...] = ()

    @property
    def module(self) -> str:
        parts = self.handler_qualname.rsplit(".", 1)
        return parts[0] if len(parts) > 1 else ""


@dataclass(frozen=True)
class InputAccessFact:
    """A discovered access to request input data."""

    function_qualname: str  # which function contains this access
    location: Location
    source: InputSource  # where data comes from
    accessor: AccessorKind  # how data is retrieved
    key_expr: str | None  # the key expression (may be dynamic)
    key_literal: str | None  # resolved literal key, if statically known
    raw_code: str  # the source text of the access
    notes: tuple[str, ...] = ()

    @property
    def module(self) -> str:
        parts = self.function_qualname.rsplit(".", 1)
        return parts[0] if len(parts) > 1 else ""


@dataclass(frozen=True)
class CallEdge:
    """A function-to-function call relationship."""

    caller_qualname: str
    callee_qualname: str
    location: Location
    argument_map: dict[int, str] | None = None  # positional -> what's passed (e.g. "request.form")

    def __hash__(self) -> int:
        return hash((self.caller_qualname, self.callee_qualname, self.location))


@dataclass(frozen=True)
class BeforeRequestFact:
    """A before_request middleware registration."""

    function_qualname: str
    blueprint: str | None
    location: Location


@dataclass(frozen=True)
class DictMergeFact:
    """A dict merge/unpack that could allow overwrite (e.g. {**user_data, **safe_data})."""

    function_qualname: str
    location: Location
    sources: tuple[str, ...]  # names of the merged dicts in order
    raw_code: str


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


class Severity(Enum):
    """Finding severity."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Finding:
    """A detected confusion vulnerability."""

    rule_id: str
    title: str
    description: str
    severity: Severity
    location: Location
    evidence: list[InputAccessFact | RouteFact | DictMergeFact]
    endpoint: RouteFact | None = None
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.rule_id}: {self.title} at {self.location}"

    def _repr_html_(self) -> str:
        """Rich notebook rendering for bare Finding expressions."""
        from .reporting.display import _finding_html

        return _finding_html(self)
