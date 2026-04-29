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
from .rules_support import (
    _build_parameter_site_pairs,
    _build_parameter_sites_for_family,
    _build_source_site_pairs,
    _build_source_sites_for_key,
    _find_parameter_families,
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
# CONF-001-OLD: Dual-Source Confusion
# Same key accessed from different input sources in the same endpoint's
# reachable call tree. E.g. request.args.get("item") in one place and
# request.form.get("item") in another.
# ---------------------------------------------------------------------------


@rule("CONF-001-OLD")
def dual_source_confusion_old(graph: AnalysisGraph) -> list[Finding]:
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
                    rule_id="CONF-001-OLD",
                    title=f"Key '{key}' accessed from multiple sources: {_fmt_sources(sources)}",
                    description=(
                        f"Within endpoint {handler}, the key '{key}' is read from "
                        f"{_fmt_sources(sources)}. An attacker may supply the key via one "
                        f"source to pass a security check while the business logic reads "
                        f"from another source."
                    ),
                    severity=Severity.HIGH,
                    location_1=key_accesses[0].location,
                    evidence=list(key_accesses),
                    location_2=key_accesses[0].location if len(key_accesses) > 1 else None,
                    endpoint=routes[0] if routes else None,
                    details={"key": key, "sources": [s.value for s in sources]},
                )
            )

    return findings


# ---------------------------------------------------------------------------
# CONF-001: Dual-Source Confusion (Policy-Paired)
# Same key interpreted through different source-selection policies in the same
# endpoint. A single fallback site is not enough; the rule first builds
# reviewer-visible policy sites and then reports only disagreeing site pairs.
#
# Notes:
#
# CONF-001 currently detects:
# same-key, multi-policy, multi-site disagreement
# including fallback-policy and precedence-policy disagreement
#
# It does not yet prove:
# that the sites are simultaneously relevant on one effective code path
# that the sites play conflicting roles
# that one site is security-relevant and the other is business-relevant
# that the reads are not defensive/logging/normalization logic
# ---------------------------------------------------------------------------


@rule("CONF-001")
def dual_source_confusion(graph: AnalysisGraph) -> list[Finding]:
    """Detect source-policy disagreement only when two sites can be paired."""
    findings: list[Finding] = []
    by_endpoint = _group_accesses_by_endpoint(graph)

    for handler, accesses in by_endpoint.items():
        by_key: dict[str, list[InputAccessFact]] = defaultdict(list)
        for access in accesses:
            if access.key_literal:
                by_key[access.key_literal].append(access)

        for key, key_accesses in sorted(by_key.items()):
            sites = _build_source_sites_for_key(graph, handler, key, key_accesses)
            if len(sites) < 2:
                continue

            pairs = _build_source_site_pairs(sites, handler)
            if not pairs:
                continue

            ordered_pairs = sorted(pairs, key=lambda pair: pair.sort_key(handler))
            primary_pair = ordered_pairs[0]
            primary_left, primary_right = primary_pair.sites(handler)

            paired_sites_by_key = {}
            for pair in ordered_pairs:
                for site in pair.sites(handler):
                    site_key = (
                        site.owner_function,
                        site.site_kind,
                        site.report_location.file,
                        site.report_location.line,
                        site.report_location.col,
                        site.policy.identity(),
                    )
                    paired_sites_by_key[site_key] = site

            ordered = sorted(
                paired_sites_by_key.values(),
                key=lambda site: site.sort_key(handler),
            )
            sources = {
                source
                for site in ordered
                for source in site.policy.sources
            }

            evidence: list[InputAccessFact] = []
            seen_evidence: set[tuple] = set()
            for site in ordered:
                for fact in site.evidence:
                    evidence_key = (
                        fact.function_qualname,
                        fact.location.file,
                        fact.location.line,
                        fact.location.col,
                        fact.source.value,
                        fact.accessor.value,
                        fact.key_literal,
                        fact.raw_code,
                    )
                    if evidence_key in seen_evidence:
                        continue
                    seen_evidence.add(evidence_key)
                    evidence.append(fact)

            routes = graph.routes_for_handler(handler)
            findings.append(
                Finding(
                    rule_id="CONF-001",
                    title=(
                        f"Key '{key}' interpreted with conflicting source policies: "
                        f"{primary_left.policy.display()} vs {primary_right.policy.display()}"
                    ),
                    description=(
                        f"Within endpoint {handler}, the key '{key}' is interpreted through "
                        f"different source-selection policies at distinct code sites. "
                        f"A single local fallback expression is kept as one site and is only "
                        f"reported when it can be paired with another site that uses a "
                        f"different policy."
                    ),
                    severity=Severity.HIGH,
                    location_1=primary_left.report_location,
                    evidence=evidence,
                    location_2=primary_right.report_location,
                    endpoint=routes[0] if routes else None,
                    details={
                        "key": key,
                        "sources": [
                            source.value for source in sorted(sources, key=lambda s: s.value)
                        ],
                        "confidence": primary_pair.confidence.value,
                        "pair_count": len(ordered_pairs),
                        "site_count": len(ordered),
                        "sites": [site.as_details() for site in ordered],
                        "pairs": [pair.as_details(handler) for pair in ordered_pairs],
                    },
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
                    location_1=key_accesses[0].location,
                    evidence=key_accesses + partner_accesses,
                    location_2=key_accesses[0].location if len(key_accesses) > 1 else None,
                    endpoint=routes[0] if routes else None,
                    details={"key_a": key, "key_b": partner},
                )
            )

    return findings


# ---------------------------------------------------------------------------
# CONF-002-NEW: Dual-Parameter Confusion (Policy-Paired)
# Same logical parameter family interpreted through different parameter-name
# policies in the same endpoint. Unlike CONF-002, this rule does not report
# every endpoint that merely mentions both singular and plural names. It first
# builds reviewer-visible sites, then reports only disagreeing site pairs.
#
# Notes:
#
# CONF-002-NEW currently detects:
# singular/plural policy disagreement, including opposite fallback precedence
# helper-call sites lifted from propagated parameter accesses
# singleton item/items pairs when there is a validation/check signal
#
# It does not yet prove:
# that the sites are simultaneously relevant on one effective path
# that a defensive consistency check cannot reject the ambiguity
# semantic aliases that are not simple singular/plural pairs
# dynamic key flow through helper parameters
# ---------------------------------------------------------------------------


@rule("CONF-002-NEW")
def dual_parameter_confusion_policy_paired(graph: AnalysisGraph) -> list[Finding]:
    """Detect singular/plural parameter-policy disagreement between sites."""
    findings: list[Finding] = []
    by_endpoint = _group_accesses_by_endpoint(graph)

    for handler, accesses in by_endpoint.items():
        keyed = [access for access in accesses if access.key_literal]
        keys = {access.key_literal for access in keyed if access.key_literal}
        families = _find_parameter_families(keys)

        for family in families:
            family_accesses = [
                access
                for access in keyed
                if access.key_literal in {family.singular, family.plural}
            ]
            sites = _build_parameter_sites_for_family(
                graph,
                handler,
                family,
                family_accesses,
            )
            if len(sites) < 2:
                continue

            pairs = _build_parameter_site_pairs(graph, sites, handler)
            if not pairs:
                continue

            ordered_pairs = sorted(pairs, key=lambda pair: pair.sort_key(handler))
            primary_pair = ordered_pairs[0]
            primary_left, primary_right = primary_pair.sites(handler)

            paired_sites_by_key = {}
            for pair in ordered_pairs:
                for site in pair.sites(handler):
                    site_key = (
                        site.owner_function,
                        site.component_function,
                        site.site_kind,
                        site.report_location.file,
                        site.report_location.line,
                        site.report_location.col,
                        site.policy.identity(),
                    )
                    paired_sites_by_key[site_key] = site

            ordered_sites = sorted(
                paired_sites_by_key.values(),
                key=lambda site: site.sort_key(handler),
            )

            evidence: list[InputAccessFact] = []
            seen_evidence: set[tuple] = set()
            for site in ordered_sites:
                for fact in site.evidence:
                    evidence_key = (
                        fact.function_qualname,
                        fact.location.file,
                        fact.location.line,
                        fact.location.col,
                        fact.source.value,
                        fact.accessor.value,
                        fact.key_literal,
                        fact.raw_code,
                    )
                    if evidence_key in seen_evidence:
                        continue
                    seen_evidence.add(evidence_key)
                    evidence.append(fact)

            routes = graph.routes_for_handler(handler)
            findings.append(
                Finding(
                    rule_id="CONF-002-NEW",
                    title=(
                        f"Parameter family '{family.display()}' interpreted with "
                        f"conflicting policies: {primary_left.policy.display()} vs "
                        f"{primary_right.policy.display()}"
                    ),
                    description=(
                        f"Within endpoint {handler}, the parameter family "
                        f"'{family.display()}' is interpreted through different "
                        f"singular/plural policies at distinct code sites. "
                        f"A single local compatibility fallback is kept as one site "
                        f"and is only reported when paired with another site that "
                        f"uses a different policy."
                    ),
                    severity=Severity.HIGH,
                    location_1=primary_left.report_location,
                    evidence=evidence,
                    location_2=primary_right.report_location,
                    endpoint=routes[0] if routes else None,
                    details={
                        "family": family.display(),
                        "singular": family.singular,
                        "plural": family.plural,
                        "confidence": primary_pair.confidence.value,
                        "pair_count": len(ordered_pairs),
                        "site_count": len(ordered_sites),
                        "sites": [site.as_details() for site in ordered_sites],
                        "pairs": [pair.as_details(handler) for pair in ordered_pairs],
                    },
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
                        location_1=key_accesses[0].location,
                        evidence=list(key_accesses),
                        location_2=key_accesses[0].location if len(key_accesses) > 1 else None,
                        endpoint=routes[0] if routes else None,
                        details={"key": key, "accessors": [a.value for a in accessors]},
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# CONF-004: Values Merge Confusion
# request.values reads Flask's merged args+form view. This is only a strong
# confusion candidate when the same key is also read from request.args or
# request.form in the endpoint context. Mixed-key use remains a low-confidence
# review signal because it often marks action code accepting query overrides,
# but it does not by itself prove semantic disagreement.
# ---------------------------------------------------------------------------


@rule("CONF-004")
def values_merge_confusion(graph: AnalysisGraph) -> list[Finding]:
    """Detect request.values paired with args/form, prioritizing same-key pairs."""
    findings: list[Finding] = []
    by_endpoint = _group_accesses_by_endpoint(graph)

    for handler, accesses in by_endpoint.items():
        by_key: dict[str, list[InputAccessFact]] = defaultdict(list)
        for access in accesses:
            if access.key_literal:
                by_key[access.key_literal].append(access)

        routes = graph.routes_for_handler(handler)
        emitted_same_key = False
        for key, key_accesses in sorted(by_key.items()):
            values_accesses = [
                access for access in key_accesses if access.source == InputSource.VALUES
            ]
            specific_accesses = [
                access
                for access in key_accesses
                if access.source in {InputSource.ARGS, InputSource.FORM}
            ]
            if not values_accesses or not specific_accesses:
                continue

            emitted_same_key = True
            specific_sources = {
                access.source for access in specific_accesses
            }
            specific_names = _fmt_sources(specific_sources)
            findings.append(
                Finding(
                    rule_id="CONF-004",
                    title=f"Key '{key}' read through request.values and {specific_names}",
                    description=(
                        f"Within endpoint {handler}, the key '{key}' is read from "
                        f"request.values (Flask's merged args+form view) and from "
                        f"{specific_names}. This is a same-key source-policy disagreement: "
                        f"the values site can observe query-string input that the "
                        f"specific-source site does not intend to read."
                    ),
                    severity=Severity.MEDIUM,
                    location_1=values_accesses[0].location,
                    evidence=values_accesses + specific_accesses,
                    location_2=specific_accesses[0].location,
                    endpoint=routes[0] if routes else None,
                    details={
                        "key": key,
                        "specific_sources": [
                            source.value
                            for source in sorted(specific_sources, key=lambda s: s.value)
                        ],
                        "signal": "same_key_values_pair",
                    },
                )
            )

        if emitted_same_key:
            continue

        values_accesses = [access for access in accesses if access.source == InputSource.VALUES]
        specific_accesses = [
            access for access in accesses if access.source in {InputSource.ARGS, InputSource.FORM}
        ]
        if not values_accesses or not specific_accesses:
            continue

        sources = {access.source for access in specific_accesses}
        specific_names = _fmt_sources(sources)
        findings.append(
            Finding(
                rule_id="CONF-004",
                title=f"request.values mixed with {specific_names} on different keys",
                description=(
                    f"Within endpoint {handler}, request.values is used alongside "
                    f"{specific_names}, but no same-key values/args-or-form pair was found. "
                    f"This is a low-confidence review signal rather than a confirmed "
                    f"confusion candidate, because the accesses may intentionally read "
                    f"different parameters."
                ),
                severity=Severity.INFO,
                location_1=values_accesses[0].location,
                evidence=values_accesses + specific_accesses,
                location_2=specific_accesses[0].location,
                endpoint=routes[0] if routes else None,
                details={
                    "mixed_sources": [
                        source.value
                        for source in sorted(
                            sources | {InputSource.VALUES},
                            key=lambda s: s.value,
                        )
                    ],
                    "signal": "mixed_key_values_usage",
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
                                location_1=ma.location,
                                evidence=[ma, ha],
                                location_2=None,
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
# Helpers
# ---------------------------------------------------------------------------


def _fmt_sources(sources: set[InputSource]) -> str:
    names = sorted(s.value for s in sources)
    if len(names) == 1:
        return f"request.{names[0]}"
    return " and ".join(f"request.{n}" for n in names)
