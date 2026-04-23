"""Detection rules for confusion/inconsistent interpretation vulnerabilities.

Each rule is a function that takes an AnalysisGraph and returns Findings.
Rules operate ONLY on normalized facts -- they never import from backends.

Rules are registered via the @rule decorator and discovered automatically.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from ..analysis.graph import AnalysisGraph
from ..models import (
    AccessorKind,
    Finding,
    InputAccessFact,
    InputSource,
    Severity,
)

# ---------------------------------------------------------------------------
# Rule Registry
# ---------------------------------------------------------------------------

_RULES: dict[str, Callable[[AnalysisGraph], list[Finding]]] = {}


def rule(rule_id: str):
    """Register a detection rule."""

    def decorator(fn: Callable[[AnalysisGraph], list[Finding]]) -> Callable:
        _RULES[rule_id] = fn
        fn.rule_id = rule_id
        return fn

    return decorator


def get_all_rules() -> dict[str, Callable[[AnalysisGraph], list[Finding]]]:
    return dict(_RULES)


def run_all_rules(graph: AnalysisGraph) -> list[Finding]:
    findings: list[Finding] = []
    for rule_fn in _RULES.values():
        findings.extend(rule_fn(graph))
    return findings


def run_rules(graph: AnalysisGraph, rule_ids: list[str] | None = None) -> list[Finding]:
    if rule_ids is None:
        return run_all_rules(graph)
    findings: list[Finding] = []
    for rid in rule_ids:
        if rid in _RULES:
            findings.extend(_RULES[rid](graph))
    return findings


# ---------------------------------------------------------------------------
# Helper: Group accesses by endpoint
# ---------------------------------------------------------------------------


def _group_accesses_by_endpoint(graph: AnalysisGraph) -> dict[str, list[InputAccessFact]]:
    """For each endpoint handler, collect all input accesses reachable from it."""
    result: dict[str, list[InputAccessFact]] = {}
    for route in graph.routes:
        handler = route.handler_qualname
        accesses = graph.accesses_reachable_from(handler)
        if accesses:
            result[handler] = accesses
    return result


# ---------------------------------------------------------------------------
# CONF-001: Dual-Source Confusion
# Same key accessed from different input sources in the same endpoint's
# reachable call tree. E.g. request.args.get("item") in one place and
# request.form.get("item") in another.
# ---------------------------------------------------------------------------


@rule("CONF-001")
def dual_source_confusion(graph: AnalysisGraph) -> list[Finding]:
    """Detect same key accessed from different sources within an endpoint."""
    findings: list[Finding] = []
    by_endpoint = _group_accesses_by_endpoint(graph)

    for handler, accesses in by_endpoint.items():
        by_key: dict[str, list[InputAccessFact]] = defaultdict(list)
        for a in accesses:
            if a.key_literal:
                by_key[a.key_literal].append(a)

        for key, key_accesses in by_key.items():
            sources = {a.source for a in key_accesses}
            # Ignore if all accesses are from the same source
            if len(sources) <= 1:
                continue
            # Check for meaningful source divergence
            # values is a superset of args+form, so args vs values or form vs values is a finding
            routes = graph.routes_for_handler(handler)
            findings.append(
                Finding(
                    rule_id="CONF-001",
                    title=f"Key '{key}' accessed from multiple sources: {_fmt_sources(sources)}",
                    description=(
                        f"Within endpoint {handler}, the key '{key}' is read from "
                        f"{_fmt_sources(sources)}. An attacker may supply the key via one "
                        f"source to pass a security check while the business logic reads "
                        f"from another source."
                    ),
                    severity=Severity.HIGH,
                    location=key_accesses[0].location,
                    evidence=list(key_accesses),
                    endpoint=routes[0] if routes else None,
                    details={"key": key, "sources": [s.value for s in sources]},
                )
            )

    return findings


# ---------------------------------------------------------------------------
# CONF-002: Dual-Parameter Confusion
# Same logical data accessed via different parameter names.
# E.g. "item" (singular) vs "items" (plural) for the same concept.
# Heuristic: parameters that differ only by a trailing 's', or that are
# accessed with get() vs getlist() suggesting singular/plural confusion.
# ---------------------------------------------------------------------------


@rule("CONF-002")
def dual_parameter_confusion(graph: AnalysisGraph) -> list[Finding]:
    """Detect singular/plural parameter name confusion."""
    findings: list[Finding] = []
    by_endpoint = _group_accesses_by_endpoint(graph)

    for handler, accesses in by_endpoint.items():
        keyed = [a for a in accesses if a.key_literal]
        keys = {a.key_literal for a in keyed}

        # Check for singular/plural pairs
        for key in keys:
            plural = key + "s"
            singular = key.rstrip("s") if key.endswith("s") and len(key) > 2 else None

            partner = None
            if plural in keys:
                partner = plural
            elif singular and singular in keys:
                partner = singular

            if partner is None or partner <= key:
                continue

            key_accesses = [a for a in keyed if a.key_literal == key]
            partner_accesses = [a for a in keyed if a.key_literal == partner]

            routes = graph.routes_for_handler(handler)
            findings.append(
                Finding(
                    rule_id="CONF-002",
                    title=f"Parameter name confusion: '{key}' vs '{partner}'",
                    description=(
                        f"Within endpoint {handler}, both '{key}' and '{partner}' are accessed. "
                        f"If these represent the same logical value in singular/plural form, "
                        f"an attacker may supply one to affect business logic while the security "
                        f"check reads the other."
                    ),
                    severity=Severity.HIGH,
                    location=key_accesses[0].location,
                    evidence=key_accesses + partner_accesses,
                    endpoint=routes[0] if routes else None,
                    details={"key_a": key, "key_b": partner},
                )
            )

    return findings


# ---------------------------------------------------------------------------
# CONF-003: Cardinality Confusion
# Same key accessed with get() (single value) and getlist() (all values)
# in the same endpoint. The caller gets different data depending on which
# accessor is used.
# ---------------------------------------------------------------------------


@rule("CONF-003")
def cardinality_confusion(graph: AnalysisGraph) -> list[Finding]:
    """Detect get() vs getlist() on the same key within an endpoint."""
    findings: list[Finding] = []
    by_endpoint = _group_accesses_by_endpoint(graph)

    for handler, accesses in by_endpoint.items():
        by_key: dict[str, list[InputAccessFact]] = defaultdict(list)
        for a in accesses:
            if a.key_literal and a.accessor in (
                AccessorKind.GET,
                AccessorKind.GETLIST,
                AccessorKind.INDEX,
            ):
                by_key[a.key_literal].append(a)

        for key, key_accesses in by_key.items():
            accessors = {a.accessor for a in key_accesses}
            has_single = accessors & {AccessorKind.GET, AccessorKind.INDEX}
            has_multi = AccessorKind.GETLIST in accessors

            if has_single and has_multi:
                routes = graph.routes_for_handler(handler)
                findings.append(
                    Finding(
                        rule_id="CONF-003",
                        title=f"Cardinality confusion on key '{key}': get() vs getlist()",
                        description=(
                            f"Within endpoint {handler}, the key '{key}' is accessed with both "
                            f"single-value (.get() or []) and multi-value (.getlist()) accessors. "
                            f"Security checks using .get() see only the first value while business "
                            f"logic using .getlist() processes all values."
                        ),
                        severity=Severity.HIGH,
                        location=key_accesses[0].location,
                        evidence=list(key_accesses),
                        endpoint=routes[0] if routes else None,
                        details={"key": key, "accessors": [a.value for a in accessors]},
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# CONF-004: Values Merge Confusion
# request.values is used alongside request.args or request.form.
# Since values = args + form (with args taking precedence), using both
# can lead to the same parameter being read from different effective sources.
# ---------------------------------------------------------------------------


@rule("CONF-004")
def values_merge_confusion(graph: AnalysisGraph) -> list[Finding]:
    """Detect request.values used alongside request.args or request.form."""
    findings: list[Finding] = []
    by_endpoint = _group_accesses_by_endpoint(graph)

    for handler, accesses in by_endpoint.items():
        sources = {a.source for a in accesses}
        has_values = InputSource.VALUES in sources
        has_specific = sources & {InputSource.ARGS, InputSource.FORM}

        if has_values and has_specific:
            values_accesses = [a for a in accesses if a.source == InputSource.VALUES]
            specific_accesses = [
                a for a in accesses if a.source in {InputSource.ARGS, InputSource.FORM}
            ]
            specific_names = _fmt_sources(sources & {InputSource.ARGS, InputSource.FORM})

            routes = graph.routes_for_handler(handler)
            findings.append(
                Finding(
                    rule_id="CONF-004",
                    title=f"request.values used alongside {specific_names}",
                    description=(
                        f"Within endpoint {handler}, request.values (merged args+form) is used "
                        f"alongside {specific_names}. Since request.values combines both sources "
                        f"with args taking precedence, an attacker can inject values via query "
                        f"string that the form-specific code path doesn't see."
                    ),
                    severity=Severity.MEDIUM,
                    location=values_accesses[0].location,
                    evidence=values_accesses + specific_accesses,
                    endpoint=routes[0] if routes else None,
                    details={"mixed_sources": [s.value for s in sources]},
                )
            )

    return findings


# ---------------------------------------------------------------------------
# CONF-005: Dict Merge Overwrite
# Patterns like {**user_data, **safe_data} where user-controlled data
# is merged with computed/safe data. If the user data dict is unpacked
# first, its keys can be overwritten. If it's unpacked second, it can
# overwrite safe computed values.
# ---------------------------------------------------------------------------


@rule("CONF-005")
def dict_merge_overwrite(graph: AnalysisGraph) -> list[Finding]:
    """Detect dict merge patterns that may allow user data to overwrite safe values."""
    findings: list[Finding] = []

    for route in graph.routes:
        handler = route.handler_qualname
        merges = graph.merges_reachable_from(handler)

        for merge in merges:
            # Heuristic: look for a merge where one source is user-controlled
            user_controlled_idx = None
            safe_idx = None

            for i, src in enumerate(merge.sources):
                src_lower = src.lower()
                if any(
                    kw in src_lower
                    for kw in ["user_data", "request", "form", "json", "input", "payload"]
                ):
                    user_controlled_idx = i
                elif any(kw in src_lower for kw in ["safe", "computed", "order", "result"]):
                    safe_idx = i

            if user_controlled_idx is not None:
                severity = Severity.HIGH
                if safe_idx is not None and user_controlled_idx < safe_idx:
                    severity = Severity.MEDIUM
                    note = "User data is unpacked before safe data (safe values win on collision)"
                else:
                    note = "User data is unpacked AFTER safe data (user values can overwrite!)"

                findings.append(
                    Finding(
                        rule_id="CONF-005",
                        title=f"Dict merge with user-controlled data: {merge.raw_code[:80]}",
                        description=(
                            f"In {merge.function_qualname}, a dict merge unpacks user-controlled "
                            f"data alongside other values. {note}. Fields like 'total', 'user_id', "
                            f"or 'order_id' in the user data could overwrite computed values."
                        ),
                        severity=severity,
                        location=merge.location,
                        evidence=[merge],
                        endpoint=route,
                        details={
                            "sources": list(merge.sources),
                            "user_controlled_position": user_controlled_idx,
                        },
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# CONF-006: Middleware/Handler Source Divergence
# When a before_request middleware and the endpoint handler read the same
# parameter from different sources or using different accessor logic.
# ---------------------------------------------------------------------------


@rule("CONF-006")
def middleware_handler_divergence(graph: AnalysisGraph) -> list[Finding]:
    """Detect when middleware and handler use different sources for the same key."""
    findings: list[Finding] = []

    for route in graph.routes:
        handler = route.handler_qualname
        blueprint = route.blueprint

        # Find before_request middleware for this blueprint
        middleware_funcs = graph.before_requests_for(blueprint)
        if not middleware_funcs:
            continue

        handler_accesses = graph.accesses_reachable_from(handler)
        handler_keys: dict[str, list[InputAccessFact]] = defaultdict(list)
        for a in handler_accesses:
            if a.key_literal:
                handler_keys[a.key_literal].append(a)

        for mw in middleware_funcs:
            mw_accesses = graph.accesses_reachable_from(mw.function_qualname)
            for ma in mw_accesses:
                if not ma.key_literal:
                    continue
                if ma.key_literal not in handler_keys:
                    continue

                for ha in handler_keys[ma.key_literal]:
                    if ma.source != ha.source or ma.accessor != ha.accessor:
                        findings.append(
                            Finding(
                                rule_id="CONF-006",
                                title=(
                                    f"Middleware/handler divergence on '{ma.key_literal}': "
                                    f"middleware uses {ma.source.value}.{ma.accessor.value}(), "
                                    f"handler uses {ha.source.value}.{ha.accessor.value}()"
                                ),
                                description=(
                                    f"The before_request middleware {mw.function_qualname} reads "
                                    f"'{ma.key_literal}' from {ma.source.value} using {ma.accessor.value}(), "
                                    f"but the handler {handler} reads it from {ha.source.value} using "
                                    f"{ha.accessor.value}(). An attacker can supply the parameter via the "
                                    f"source the middleware doesn't check to bypass validation."
                                ),
                                severity=Severity.HIGH,
                                location=ma.location,
                                evidence=[ma, ha],
                                endpoint=route,
                                details={
                                    "key": ma.key_literal,
                                    "middleware_source": ma.source.value,
                                    "handler_source": ha.source.value,
                                },
                            )
                        )

    return findings


# ---------------------------------------------------------------------------
# CONF-007: Conditional Source Selection
# Patterns like: data = request.json if request.is_json else request.form
# followed by a get() call. This means the effective source depends on
# Content-Type, which is attacker-controlled.
# ---------------------------------------------------------------------------


@rule("CONF-007")
def conditional_source_selection(graph: AnalysisGraph) -> list[Finding]:
    """Detect conditional source selection patterns."""
    findings: list[Finding] = []
    by_endpoint = _group_accesses_by_endpoint(graph)

    for handler, accesses in by_endpoint.items():
        # Look for the pattern: both JSON and FORM sources accessed in same endpoint
        # where one of them is via a conditional (ternary) expression
        json_accesses = [a for a in accesses if a.source == InputSource.JSON]
        form_accesses = [a for a in accesses if a.source == InputSource.FORM]

        if json_accesses and form_accesses:
            # Check if any dict merges in this handler use the conditionally-selected data
            merges = graph.merges_reachable_from(handler)
            if merges:
                routes = graph.routes_for_handler(handler)
                findings.append(
                    Finding(
                        rule_id="CONF-007",
                        title="Conditional source selection with dict merge",
                        description=(
                            f"Endpoint {handler} reads from both request.json and request.form "
                            f"(likely via a conditional like `request.json if request.is_json else request.form`), "
                            f"then merges user-controlled data into a dict. The effective source "
                            f"depends on Content-Type, which is attacker-controlled."
                        ),
                        severity=Severity.MEDIUM,
                        location=json_accesses[0].location,
                        evidence=json_accesses + form_accesses,
                        endpoint=routes[0] if routes else None,
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_sources(sources: set[InputSource]) -> str:
    names = sorted(s.value for s in sources)
    if len(names) == 1:
        return f"request.{names[0]}"
    return " and ".join(f"request.{n}" for n in names)
