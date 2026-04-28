"""Support helpers for detection rules.

This module keeps rule-focused data structures out of ``rules.py`` so the rule
functions stay readable. The common abstraction is a reviewer-visible *site*:
one code place that interprets request input. Each rule then supplies its own
policy model for what disagreement means.

For CONF-001, a site describes how one key selects a request source. For
CONF-002-NEW, a site describes how one singular/plural parameter family is
interpreted. The intended pipeline is:

raw facts -> normalized observations -> sites -> site pairs -> findings
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from ..analysis.graph import AnalysisGraph
from ..models import AccessorKind, InputAccessFact, InputSource, Location


class SiteConfidence(Enum):
    """How strongly a site is supported by the currently available facts."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class _SourcePolicy:
    """How one code site chooses request data for a key.

    ``ordered`` is intentionally explicit. A ternary fallback such as
    ``request.json if request.is_json else request.form`` is treated as an
    unordered conditional policy for the current fact model, because the facts
    do not preserve enough condition semantics to distinguish the equivalent
    inverse spelling. An ``or`` chain is ordered because precedence is the
    security-relevant behavior.
    """

    sources: tuple[InputSource, ...]
    policy_kind: str  # single_source | fallback_policy | precedence_policy
    ordered: bool

    def identity(self) -> tuple[str, bool, tuple[str, ...]]:
        """Return the comparison identity used when pairing sites."""
        if self.ordered:
            source_names = tuple(source.value for source in self.sources)
        else:
            source_names = tuple(sorted({source.value for source in self.sources}))
        return (self.policy_kind, self.ordered, source_names)

    def display(self) -> str:
        """Return a compact reviewer-facing policy description."""
        names = [f"request.{source.value}" for source in self.sources]
        if len(names) == 1:
            return names[0]
        if self.ordered:
            return " -> ".join(names)
        return " / ".join(sorted(set(names)))


@dataclass(frozen=True)
class _NormalizedAccessObservation:
    """One normalized request-key observation derived from raw access facts.

    A normalized observation is still not a confusion candidate on its own.
    Its purpose is only to clean up extractor output before the rule reasons
    about disagreement between code locations.
    """

    key: str
    policy: _SourcePolicy
    function_qualname: str
    location: Location
    accessor: AccessorKind
    raw_code: str
    facts: tuple[InputAccessFact, ...]
    propagated: bool


@dataclass(frozen=True)
class _SourceSite:
    """One reviewer-visible place in the code that consumes request data.

    A site is a suspicious interpretation point, not a finding. A finding
    requires at least two source sites that disagree about the policy used for
    the same key in the same endpoint context.

    Site = suspicious code place
    Pair = two suspicious sites that disagree
    Candidate for confusion = a meaningful pair
    """

    key: str
    policy: _SourcePolicy
    site_kind: str  # direct | helper_call | middleware | helper_body
    owner_function: str
    report_location: Location
    evidence: tuple[InputAccessFact, ...]
    confidence: SiteConfidence

    def sort_key(self, handler: str) -> tuple:
        """Keep result ordering deterministic and handler-focused."""
        return (
            self.owner_function != handler,
            self.site_kind not in {"direct", "middleware"},
            self.report_location.file,
            self.report_location.line,
            self.report_location.col,
            self.owner_function,
            self.policy.display(),
            self.key,
        )

    def as_details(self) -> dict[str, str]:
        """Serialize the site in a simple way for Finding.details."""
        return {
            "key": self.key,
            "policy": self.policy.display(),
            "policy_kind": self.policy.policy_kind,
            "site_kind": self.site_kind,
            "owner_function": self.owner_function,
            "location": str(self.report_location),
            "confidence": self.confidence.value,
        }


@dataclass(frozen=True)
class _SourceSitePair:
    """Two same-key sites whose source policies disagree."""

    first: _SourceSite
    second: _SourceSite
    confidence: SiteConfidence

    def sites(self, handler: str) -> tuple[_SourceSite, _SourceSite]:
        """Return pair sites in deterministic report order."""
        ordered = sorted((self.first, self.second), key=lambda site: site.sort_key(handler))
        return ordered[0], ordered[1]

    def all_sources(self) -> set[InputSource]:
        """Return all concrete request sources mentioned by the pair."""
        return set(self.first.policy.sources) | set(self.second.policy.sources)

    def sort_key(self, handler: str) -> tuple:
        """Sort high-confidence, handler-focused pairs first."""
        left, right = self.sites(handler)
        return (
            -_confidence_rank(self.confidence),
            left.sort_key(handler),
            right.sort_key(handler),
            self.first.policy.display(),
            self.second.policy.display(),
        )

    def as_details(self, handler: str) -> dict[str, str]:
        """Serialize the pair in a simple way for Finding.details."""
        left, right = self.sites(handler)
        return {
            "left_policy": left.policy.display(),
            "left_location": str(left.report_location),
            "left_kind": left.site_kind,
            "right_policy": right.policy.display(),
            "right_location": str(right.report_location),
            "right_kind": right.site_kind,
            "confidence": self.confidence.value,
        }


@dataclass(frozen=True)
class _ParameterFamily:
    """A simple singular/plural logical parameter family.

    The rule intentionally starts with conservative English pluralization:
    ``item`` -> ``items`` and ``item_id`` -> ``item_ids``. More aggressive
    stemming creates bad review noise for words such as ``status`` and should
    be added only after fixture coverage proves it is worth the cost.
    """

    singular: str
    plural: str

    def display(self) -> str:
        """Return a compact reviewer-facing family label."""
        return f"{self.singular}/{self.plural}"


@dataclass(frozen=True)
class _ParameterPolicy:
    """How one site interprets a singular/plural parameter family.

    ``keys`` is ordered because fallback and precedence order is meaningful for
    this rule. ``item -> items`` and ``items -> item`` are different policies.
    """

    family: _ParameterFamily
    keys: tuple[str, ...]
    policy_kind: str  # single_parameter | variant_policy
    ordered: bool = True

    def identity(self) -> tuple[str, bool, tuple[str, ...]]:
        """Return the comparison identity used when pairing parameter sites."""
        return (self.policy_kind, self.ordered, self.keys)

    def display(self) -> str:
        """Return a compact reviewer-facing policy description."""
        quoted = [f"'{key}'" for key in self.keys]
        if len(quoted) == 1:
            return quoted[0]
        return " -> ".join(quoted)


@dataclass(frozen=True)
class _ParameterSite:
    """One reviewer-visible interpretation of a parameter-name family."""

    family: _ParameterFamily
    policy: _ParameterPolicy
    site_kind: str  # direct | helper_call | middleware | helper_body
    owner_function: str
    component_function: str
    report_location: Location
    evidence: tuple[InputAccessFact, ...]
    confidence: SiteConfidence

    def sort_key(self, handler: str) -> tuple:
        """Keep result ordering deterministic and handler-focused."""
        return (
            self.owner_function != handler,
            self.site_kind not in {"direct", "middleware"},
            self.report_location.file,
            self.report_location.line,
            self.report_location.col,
            self.owner_function,
            self.component_function,
            self.policy.display(),
            self.family.display(),
        )

    def as_details(self) -> dict[str, str]:
        """Serialize the site in a simple way for Finding.details."""
        return {
            "family": self.family.display(),
            "policy": self.policy.display(),
            "policy_kind": self.policy.policy_kind,
            "site_kind": self.site_kind,
            "owner_function": self.owner_function,
            "component_function": self.component_function,
            "location": str(self.report_location),
            "confidence": self.confidence.value,
        }


@dataclass(frozen=True)
class _ParameterSitePair:
    """Two sites whose parameter-family policies disagree."""

    first: _ParameterSite
    second: _ParameterSite
    confidence: SiteConfidence

    def sites(self, handler: str) -> tuple[_ParameterSite, _ParameterSite]:
        """Return pair sites in deterministic report order."""
        ordered = sorted((self.first, self.second), key=lambda site: site.sort_key(handler))
        return ordered[0], ordered[1]

    def sort_key(self, handler: str) -> tuple:
        """Sort high-confidence, handler-focused pairs first."""
        left, right = self.sites(handler)
        return (
            -_confidence_rank(self.confidence),
            left.sort_key(handler),
            right.sort_key(handler),
            self.first.policy.display(),
            self.second.policy.display(),
        )

    def as_details(self, handler: str) -> dict[str, str]:
        """Serialize the pair in a simple way for Finding.details."""
        left, right = self.sites(handler)
        return {
            "left_policy": left.policy.display(),
            "left_location": str(left.report_location),
            "left_kind": left.site_kind,
            "right_policy": right.policy.display(),
            "right_location": str(right.report_location),
            "right_kind": right.site_kind,
            "confidence": self.confidence.value,
        }


def _is_propagated_access(access: InputAccessFact) -> bool:
    """Return True when the source was inferred from a caller argument."""
    for note in access.notes:  # noqa: SIM110
        if note.startswith("propagated from caller via "):
            return True
    return False


def _confidence_rank(confidence: SiteConfidence) -> int:
    """Convert a confidence label into an orderable rank."""
    ranks = {
        SiteConfidence.LOW: 1,
        SiteConfidence.MEDIUM: 2,
        SiteConfidence.HIGH: 3,
    }
    return ranks[confidence]


def _access_sort_key(access: InputAccessFact) -> tuple:
    """Sort raw accesses in a stable way."""
    return (
        access.location.file,
        access.location.line,
        access.location.col,
        access.function_qualname,
        access.source.value,
        access.accessor.value,
        access.key_literal or "",
        access.raw_code,
        tuple(access.notes),
    )


def _unique_sources_in_order(accesses: list[InputAccessFact]) -> tuple[InputSource, ...]:
    """Return sources in the order the extractor emitted them."""
    sources: list[InputSource] = []
    seen: set[InputSource] = set()
    for access in accesses:
        if access.source in seen:
            continue
        seen.add(access.source)
        sources.append(access.source)
    return tuple(sources)


def _source_policy_from_accesses(
    accesses: list[InputAccessFact],
    policy_kind: str | None = None,
    ordered: bool | None = None,
) -> _SourcePolicy:
    """Build a source-selection policy from one grouped access bucket."""
    sources = _unique_sources_in_order(accesses)
    if len(sources) <= 1:
        return _SourcePolicy(
            sources=sources,
            policy_kind=policy_kind or "single_source",
            ordered=True if ordered is None else ordered,
        )

    return _SourcePolicy(
        sources=sources,
        policy_kind=policy_kind or "fallback_policy",
        ordered=False if ordered is None else ordered,
    )


def _make_observation(
    key: str,
    accesses: list[InputAccessFact],
    policy_kind: str | None = None,
    ordered: bool | None = None,
) -> _NormalizedAccessObservation:
    """Create one normalized observation from one grouped access bucket."""
    ordered_accesses = sorted(accesses, key=_access_sort_key)
    first = ordered_accesses[0]

    return _NormalizedAccessObservation(
        key=key,
        policy=_source_policy_from_accesses(accesses, policy_kind, ordered),
        function_qualname=first.function_qualname,
        location=first.location,
        accessor=first.accessor,
        raw_code=first.raw_code,
        facts=tuple(ordered_accesses),
        propagated=_is_propagated_access(first),
    )


def _can_combine_as_precedence_part(observation: _NormalizedAccessObservation) -> bool:
    """Return True for one direct single-source read that may be part of an or-chain."""
    return (
        not observation.propagated
        and observation.policy.policy_kind == "single_source"
        and len(observation.policy.sources) == 1
        and observation.accessor in {AccessorKind.GET, AccessorKind.INDEX}
    )


def _combine_same_line_precedence_observations(
    observations: list[_NormalizedAccessObservation],
) -> list[_NormalizedAccessObservation]:
    """Combine same-line direct reads into an ordered precedence policy.

    The fact model does not expose the parent ``BoolOp``. For expressions like
    ``request.args.get("coupon") or request.form.get("coupon")`` the two facts
    share function, line, and key, and their column order represents runtime
    precedence. Combining them prevents one expression from being treated as
    two disagreeing sites by itself, while still allowing two opposite
    precedence policies to be paired later.
    """

    groups: dict[tuple[str, str, int, str], list[_NormalizedAccessObservation]] = defaultdict(list)
    passthrough: list[_NormalizedAccessObservation] = []

    for observation in observations:
        if not _can_combine_as_precedence_part(observation):
            passthrough.append(observation)
            continue
        group_key = (
            observation.function_qualname,
            observation.location.file,
            observation.location.line,
            observation.key,
        )
        groups[group_key].append(observation)

    combined: list[_NormalizedAccessObservation] = list(passthrough)
    for grouped in groups.values():
        unique_sources = {
            source for observation in grouped for source in observation.policy.sources
        }
        if len(grouped) < 2 or len(unique_sources) < 2:
            combined.extend(grouped)
            continue

        ordered_group = sorted(
            grouped,
            key=lambda observation: (
                observation.location.col,
                observation.raw_code,
                observation.policy.display(),
            ),
        )
        facts: list[InputAccessFact] = []
        for observation in ordered_group:
            facts.extend(observation.facts)

        first = ordered_group[0]
        combined.append(
            _NormalizedAccessObservation(
                key=first.key,
                policy=_source_policy_from_accesses(
                    facts,
                    policy_kind="precedence_policy",
                    ordered=True,
                ),
                function_qualname=first.function_qualname,
                location=first.location,
                accessor=first.accessor,
                raw_code=" or ".join(observation.raw_code for observation in ordered_group),
                facts=tuple(sorted(facts, key=_access_sort_key)),
                propagated=False,
            )
        )

    combined.sort(
        key=lambda observation: (
            observation.location.file,
            observation.location.line,
            observation.location.col,
            observation.function_qualname,
            observation.policy.display(),
            observation.accessor.value,
            observation.raw_code,
        )
    )
    return combined


def _normalize_observations_for_key(
    key: str,
    key_accesses: list[InputAccessFact],
) -> list[_NormalizedAccessObservation]:
    """Normalize raw accesses for one key into policy observations."""
    grouped_accesses: dict[tuple, list[InputAccessFact]] = defaultdict(list)

    for access in key_accesses:
        propagated = _is_propagated_access(access)
        group_key: tuple = (
            access.function_qualname,
            access.location.file,
            access.location.line,
            access.location.col,
            access.accessor.value,
            access.key_literal,
            access.raw_code,
            "propagated" if propagated else "local",
        )

        # The same helper body may be called with multiple sources. Keep those
        # separate so the later site-building step can reconstruct disagreement.
        if propagated:
            group_key = group_key + (access.source.value,)

        grouped_accesses[group_key].append(access)

    observations: list[_NormalizedAccessObservation] = []
    for grouped in grouped_accesses.values():
        observations.append(_make_observation(key, grouped))

    ordered_observations = _combine_same_line_precedence_observations(observations)
    ordered_observations.sort(
        key=lambda observation: (
            observation.location.file,
            observation.location.line,
            observation.location.col,
            observation.function_qualname,
            observation.policy.display(),
            observation.accessor.value,
            observation.raw_code,
        )
    )
    return ordered_observations


def _callers_visible_from_handler(
    graph: AnalysisGraph,
    handler: str,
) -> set[str]:
    """Return functions whose locations are meaningful within this endpoint."""
    visible = set(graph.reachable_from(handler))

    routes = graph.routes_for_handler(handler)
    if routes:
        blueprint = routes[0].blueprint
        for before_request in graph.before_requests_for(blueprint):
            visible.add(before_request.function_qualname)

    return visible


def _function_is_visible(function_name: str, visible_functions: set[str]) -> bool:
    """Return True when a function name matches the endpoint-visible context.

    The current graph may contain a mixture of:
    - fully qualified names: ``utils.calculate_delivery_fee``
    - short names: ``calculate_delivery_fee``

    This helper keeps the matching rule simple and explicit so caller-visible
    helper sites are not lost just because one edge uses a shorter name.
    """

    if function_name in visible_functions:
        return True

    short_name = function_name.rsplit(".", 1)[-1]
    for visible_name in visible_functions:  # noqa: SIM110
        if visible_name.rsplit(".", 1)[-1] == short_name:
            return True

    return False


def _sources_in_code_order(code: str) -> tuple[InputSource, ...]:
    """Extract request source mentions from a source-code snippet."""
    markers = [
        ("args", InputSource.ARGS),
        ("form", InputSource.FORM),
        ("values", InputSource.VALUES),
        ("json", InputSource.JSON),
        ("get_json", InputSource.JSON),
        ("data", InputSource.DATA),
        ("headers", InputSource.HEADERS),
        ("cookies", InputSource.COOKIES),
        ("files", InputSource.FILES),
    ]

    found: list[tuple[int, InputSource]] = []
    for attr, source in markers:
        for marker in (f"request.{attr}", f".request.{attr}"):
            index = code.find(marker)
            if index >= 0:
                found.append((index, source))

    sources: list[InputSource] = []
    seen: set[InputSource] = set()
    for _, source in sorted(found, key=lambda item: item[0]):
        if source in seen:
            continue
        seen.add(source)
        sources.append(source)
    return tuple(sources)


def _source_policy_from_argument_code(code: str) -> _SourcePolicy | None:
    """Recover the source policy represented by a helper-call argument."""
    sources = _sources_in_code_order(code)
    if not sources:
        return None

    if len(sources) == 1:
        return _SourcePolicy(sources=sources, policy_kind="single_source", ordered=True)

    if " or " in code:
        return _SourcePolicy(
            sources=sources,
            policy_kind="precedence_policy",
            ordered=True,
        )

    return _SourcePolicy(
        sources=sources,
        policy_kind="fallback_policy",
        ordered=False,
    )


def _argument_policies_for_edge(edge_argument_map: dict[int, str]) -> list[_SourcePolicy]:
    """Return all source policies visible in a call edge argument map."""
    policies: list[_SourcePolicy] = []
    for argument_code in edge_argument_map.values():
        policy = _source_policy_from_argument_code(argument_code)
        if policy is not None:
            policies.append(policy)
    return policies


def _build_source_sites_for_key(
    graph: AnalysisGraph,
    handler: str,
    key: str,
    key_accesses: list[InputAccessFact],
) -> list[_SourceSite]:
    """Build semantic source-policy sites for one key inside one endpoint.

    Strategy:
    1. Normalize raw accesses into policy observations.
    2. Preserve local fallback and precedence policies as one site each.
    3. Lift propagated helper observations to endpoint-visible callsites.

    If the graph can recover the caller-visible line that passed
    ``request.form`` / ``request.values`` / etc. into a helper, that callsite
    becomes the reported location. Propagated helper facts from other endpoint
    contexts are dropped instead of becoming helper-body noise.
    """

    observations = _normalize_observations_for_key(key, key_accesses)
    routes = graph.routes_for_handler(handler)
    blueprint = routes[0].blueprint if routes else None
    visible_functions = _callers_visible_from_handler(graph, handler)
    middleware_functions = {
        before_request.function_qualname for before_request in graph.before_requests_for(blueprint)
    }

    sites: list[_SourceSite] = []

    for observation in observations:
        if not observation.propagated:
            if observation.function_qualname in middleware_functions:
                site_kind = "middleware"
                confidence = SiteConfidence.HIGH
            elif observation.function_qualname == handler:
                site_kind = "direct"
                confidence = SiteConfidence.HIGH
            else:
                site_kind = "helper_body"
                confidence = SiteConfidence.MEDIUM
            sites.append(
                _SourceSite(
                    key=key,
                    policy=observation.policy,
                    site_kind=site_kind,
                    owner_function=observation.function_qualname,
                    report_location=observation.location,
                    evidence=observation.facts,
                    confidence=confidence,
                )
            )
            continue

        if len(observation.policy.sources) != 1:
            continue

        expected_source = observation.policy.sources[0]
        found_callsite = False
        has_any_call_edge = False

        for edge in graph.call_edges_to(observation.function_qualname):
            has_any_call_edge = True
            if not _function_is_visible(edge.caller_qualname, visible_functions):
                continue
            if not edge.argument_map:
                continue

            matching_policies = [
                policy
                for policy in _argument_policies_for_edge(edge.argument_map)
                if expected_source in policy.sources
            ]
            if not matching_policies:
                continue

            site_kind = (
                "middleware" if edge.caller_qualname in middleware_functions else "helper_call"
            )
            for policy in matching_policies:
                sites.append(
                    _SourceSite(
                        key=key,
                        policy=policy,
                        site_kind=site_kind,
                        owner_function=edge.caller_qualname,
                        report_location=edge.location,
                        evidence=observation.facts,
                        confidence=SiteConfidence.HIGH,
                    )
                )
                found_callsite = True

        if not found_callsite and not has_any_call_edge:
            sites.append(
                _SourceSite(
                    key=key,
                    policy=observation.policy,
                    site_kind="helper_body",
                    owner_function=observation.function_qualname,
                    report_location=observation.location,
                    evidence=observation.facts,
                    confidence=SiteConfidence.LOW,
                )
            )

    deduplicated_sites: dict[tuple, _SourceSite] = {}
    for site in sites:
        dedupe_key = (
            site.key,
            site.policy.identity(),
            site.site_kind,
            site.owner_function,
            site.report_location.file,
            site.report_location.line,
            site.report_location.col,
        )
        existing = deduplicated_sites.get(dedupe_key)
        if existing is None or _confidence_rank(site.confidence) > _confidence_rank(
            existing.confidence
        ):
            deduplicated_sites[dedupe_key] = site

    ordered_sites = list(deduplicated_sites.values())
    ordered_sites.sort(key=lambda site: site.sort_key(handler))
    return ordered_sites


def _same_site_identity(first: _SourceSite, second: _SourceSite) -> bool:
    """Return True when two site objects point at the same reviewer-visible site."""
    return (
        first.owner_function == second.owner_function
        and first.site_kind == second.site_kind
        and first.report_location == second.report_location
        and first.policy.identity() == second.policy.identity()
        and first.key == second.key
    )


def _pair_confidence(first: _SourceSite, second: _SourceSite) -> SiteConfidence:
    """Assign coarse confidence to a disagreeing site pair."""
    weaker_rank = min(_confidence_rank(first.confidence), _confidence_rank(second.confidence))
    if weaker_rank <= _confidence_rank(SiteConfidence.LOW):
        return SiteConfidence.LOW

    if weaker_rank <= _confidence_rank(SiteConfidence.MEDIUM):
        return SiteConfidence.MEDIUM

    same_local_function = (
        first.owner_function == second.owner_function
        and first.site_kind == "direct"
        and second.site_kind == "direct"
    )
    if same_local_function:
        return SiteConfidence.MEDIUM

    return SiteConfidence.HIGH


def _build_source_site_pairs(
    sites: list[_SourceSite],
    handler: str,
) -> list[_SourceSitePair]:
    """Pair same-key sites whose source-selection policies disagree."""
    pairs: list[_SourceSitePair] = []

    for index, first in enumerate(sites):
        for second in sites[index + 1 :]:
            if _same_site_identity(first, second):
                continue
            if first.policy.identity() == second.policy.identity():
                continue

            pairs.append(
                _SourceSitePair(
                    first=first,
                    second=second,
                    confidence=_pair_confidence(first, second),
                )
            )

    pairs.sort(key=lambda pair: pair.sort_key(handler))
    return pairs


def _parameter_policy_from_observations(
    family: _ParameterFamily,
    observations: list[_NormalizedAccessObservation],
) -> _ParameterPolicy:
    """Build a parameter-name policy from ordered observations."""
    ordered_observations = sorted(
        observations,
        key=lambda observation: (
            observation.location.file,
            observation.location.line,
            observation.location.col,
            observation.raw_code,
        ),
    )
    keys: list[str] = []
    seen: set[str] = set()
    for observation in ordered_observations:
        if observation.key in seen:
            continue
        seen.add(observation.key)
        keys.append(observation.key)

    return _ParameterPolicy(
        family=family,
        keys=tuple(keys),
        policy_kind="single_parameter" if len(keys) == 1 else "variant_policy",
        ordered=True,
    )


def _find_parameter_families(keys: set[str]) -> list[_ParameterFamily]:
    """Return conservative singular/plural key families present in ``keys``."""
    families: list[_ParameterFamily] = []
    for singular in sorted(keys):
        if singular.endswith("s"):
            continue
        plural = f"{singular}s"
        if plural in keys:
            families.append(_ParameterFamily(singular=singular, plural=plural))
    return families


def _is_validation_like_name(name: str) -> bool:
    """Return True when a function name suggests checking rather than use."""
    lowered = name.rsplit(".", 1)[-1].lower()
    markers = (
        "allow",
        "available",
        "check",
        "exists",
        "require",
        "valid",
        "verify",
    )
    return any(marker in lowered for marker in markers)


def _has_validation_call_between(
    graph: AnalysisGraph,
    function_name: str,
    first_line: int,
    second_line: int,
) -> bool:
    """Return True if a validation-like call occurs between two lines."""
    lower, upper = sorted((first_line, second_line))
    for edge in graph.call_edges_from(function_name):
        if lower < edge.location.line < upper and _is_validation_like_name(edge.callee_qualname):
            return True
    return False


def _has_any_validation_boundary(
    graph: AnalysisGraph,
    function_name: str,
    observations: list[_NormalizedAccessObservation],
) -> bool:
    """Return True when observations in one function are separated by a check."""
    ordered = sorted(
        observations,
        key=lambda observation: (observation.location.line, observation.location.col),
    )
    for index, first in enumerate(ordered):
        for second in ordered[index + 1 :]:
            if first.key == second.key:
                continue
            if _has_validation_call_between(
                graph,
                function_name,
                first.location.line,
                second.location.line,
            ):
                return True
    return False


def _same_line_groups(
    observations: list[_NormalizedAccessObservation],
) -> tuple[list[list[_NormalizedAccessObservation]], list[_NormalizedAccessObservation]]:
    """Split observations into same-line multi-key groups and leftovers."""
    grouped: dict[tuple[str, str, int], list[_NormalizedAccessObservation]] = defaultdict(list)
    for observation in observations:
        group_key = (
            observation.function_qualname,
            observation.location.file,
            observation.location.line,
        )
        grouped[group_key].append(observation)

    same_line_groups: list[list[_NormalizedAccessObservation]] = []
    leftovers: list[_NormalizedAccessObservation] = []
    for group in grouped.values():
        unique_keys = {observation.key for observation in group}
        if len(group) > 1 and len(unique_keys) > 1:
            same_line_groups.append(group)
        else:
            leftovers.extend(group)

    same_line_groups.sort(
        key=lambda group: (
            group[0].location.file,
            group[0].location.line,
            min(observation.location.col for observation in group),
        )
    )
    leftovers.sort(
        key=lambda observation: (
            observation.location.file,
            observation.location.line,
            observation.location.col,
        )
    )
    return same_line_groups, leftovers


def _source_matches_argument_policy(
    observation: _NormalizedAccessObservation,
    edge_argument_map: dict[int, str] | None,
) -> bool:
    """Return True when a propagated observation matches a caller argument."""
    if not edge_argument_map:
        return False
    for policy in _argument_policies_for_edge(edge_argument_map):
        if any(source in policy.sources for source in observation.policy.sources):
            return True
    return False


def _make_parameter_site(
    family: _ParameterFamily,
    observations: list[_NormalizedAccessObservation],
    site_kind: str,
    owner_function: str,
    component_function: str,
    report_location: Location,
    confidence: SiteConfidence,
) -> _ParameterSite:
    """Create one parameter-family site from normalized observations."""
    facts: list[InputAccessFact] = []
    for observation in sorted(
        observations,
        key=lambda observation: (
            observation.location.file,
            observation.location.line,
            observation.location.col,
        ),
    ):
        facts.extend(observation.facts)

    return _ParameterSite(
        family=family,
        policy=_parameter_policy_from_observations(family, observations),
        site_kind=site_kind,
        owner_function=owner_function,
        component_function=component_function,
        report_location=report_location,
        evidence=tuple(sorted(facts, key=_access_sort_key)),
        confidence=confidence,
    )


def _direct_parameter_sites_for_handler(
    graph: AnalysisGraph,
    handler: str,
    family: _ParameterFamily,
    observations: list[_NormalizedAccessObservation],
) -> list[_ParameterSite]:
    """Build direct route sites for a parameter family.

    Same-line ``or`` expressions become one ordered policy site. Remaining
    direct reads are kept separate only when a validation-like call separates
    the two parameter variants; otherwise they are treated as one local
    compatibility/normalization site and require another disagreeing site to be
    reported.
    """
    same_line, leftovers = _same_line_groups(observations)
    sites: list[_ParameterSite] = []

    for group in same_line:
        first = sorted(group, key=lambda observation: observation.location.col)[0]
        sites.append(
            _make_parameter_site(
                family=family,
                observations=group,
                site_kind="direct",
                owner_function=handler,
                component_function=handler,
                report_location=first.location,
                confidence=SiteConfidence.HIGH,
            )
        )

    if not leftovers:
        return sites

    if _has_any_validation_boundary(graph, handler, leftovers):
        for observation in leftovers:
            sites.append(
                _make_parameter_site(
                    family=family,
                    observations=[observation],
                    site_kind="direct",
                    owner_function=handler,
                    component_function=handler,
                    report_location=observation.location,
                    confidence=SiteConfidence.HIGH,
                )
            )
        return sites

    first = leftovers[0]
    sites.append(
        _make_parameter_site(
            family=family,
            observations=leftovers,
            site_kind="direct",
            owner_function=handler,
            component_function=handler,
            report_location=first.location,
            confidence=SiteConfidence.MEDIUM,
        )
    )
    return sites


def _build_parameter_sites_for_family(
    graph: AnalysisGraph,
    handler: str,
    family: _ParameterFamily,
    family_accesses: list[InputAccessFact],
) -> list[_ParameterSite]:
    """Build reviewer-visible parameter-policy sites for one key family."""
    observations: list[_NormalizedAccessObservation] = []
    for key in (family.singular, family.plural):
        key_accesses = [access for access in family_accesses if access.key_literal == key]
        observations.extend(_normalize_observations_for_key(key, key_accesses))

    routes = graph.routes_for_handler(handler)
    blueprint = routes[0].blueprint if routes else None
    visible_functions = _callers_visible_from_handler(graph, handler)
    middleware_functions = {
        before_request.function_qualname for before_request in graph.before_requests_for(blueprint)
    }

    direct_by_function: dict[str, list[_NormalizedAccessObservation]] = defaultdict(list)
    propagated_by_function: dict[str, list[_NormalizedAccessObservation]] = defaultdict(list)

    for observation in observations:
        if observation.propagated:
            propagated_by_function[observation.function_qualname].append(observation)
        else:
            direct_by_function[observation.function_qualname].append(observation)

    sites: list[_ParameterSite] = []

    for function_name, function_observations in direct_by_function.items():
        if function_name == handler:
            sites.extend(
                _direct_parameter_sites_for_handler(
                    graph,
                    handler,
                    family,
                    function_observations,
                )
            )
            continue

        site_kind = "middleware" if function_name in middleware_functions else "helper_body"
        confidence = SiteConfidence.HIGH if site_kind == "middleware" else SiteConfidence.MEDIUM
        sites.append(
            _make_parameter_site(
                family=family,
                observations=function_observations,
                site_kind=site_kind,
                owner_function=function_name,
                component_function=function_name,
                report_location=min(
                    (observation.location for observation in function_observations),
                    key=lambda location: (location.file, location.line, location.col),
                ),
                confidence=confidence,
            )
        )

    for function_name, function_observations in propagated_by_function.items():
        found_callsite = False
        has_any_call_edge = False

        for edge in graph.call_edges_to(function_name):
            has_any_call_edge = True
            if not _function_is_visible(edge.caller_qualname, visible_functions):
                continue

            matching_observations = [
                observation
                for observation in function_observations
                if _source_matches_argument_policy(observation, edge.argument_map)
            ]
            if not matching_observations:
                continue

            site_kind = (
                "middleware" if edge.caller_qualname in middleware_functions else "helper_call"
            )
            sites.append(
                _make_parameter_site(
                    family=family,
                    observations=matching_observations,
                    site_kind=site_kind,
                    owner_function=edge.caller_qualname,
                    component_function=function_name,
                    report_location=edge.location,
                    confidence=SiteConfidence.HIGH,
                )
            )
            found_callsite = True

        if not found_callsite and not has_any_call_edge:
            sites.append(
                _make_parameter_site(
                    family=family,
                    observations=function_observations,
                    site_kind="helper_body",
                    owner_function=function_name,
                    component_function=function_name,
                    report_location=min(
                        (observation.location for observation in function_observations),
                        key=lambda location: (location.file, location.line, location.col),
                    ),
                    confidence=SiteConfidence.LOW,
                )
            )

    deduplicated_sites: dict[tuple, _ParameterSite] = {}
    for site in sites:
        dedupe_key = (
            site.family.singular,
            site.family.plural,
            site.policy.identity(),
            site.site_kind,
            site.owner_function,
            site.component_function,
            site.report_location.file,
            site.report_location.line,
            site.report_location.col,
        )
        existing = deduplicated_sites.get(dedupe_key)
        if existing is None or _confidence_rank(site.confidence) > _confidence_rank(
            existing.confidence
        ):
            deduplicated_sites[dedupe_key] = site

    ordered_sites = list(deduplicated_sites.values())
    ordered_sites.sort(key=lambda site: site.sort_key(handler))
    return ordered_sites


def _same_parameter_site_identity(first: _ParameterSite, second: _ParameterSite) -> bool:
    """Return True when two parameter sites point at the same code site."""
    return (
        first.owner_function == second.owner_function
        and first.component_function == second.component_function
        and first.site_kind == second.site_kind
        and first.report_location == second.report_location
        and first.policy.identity() == second.policy.identity()
        and first.family == second.family
    )


def _parameter_pair_has_role_signal(
    graph: AnalysisGraph,
    first: _ParameterSite,
    second: _ParameterSite,
) -> bool:
    """Return True when a single-vs-single pair has enough review signal.

    Singleton ``item`` vs ``items`` reads are common in normal compatibility
    code. To keep CONF-002-NEW usable on real projects, singleton pairs require
    some evidence that one site is acting like a check/validation component.
    Ordered variant-policy disagreements are already semantic policy
    disagreements and are handled before this helper is called.
    """
    if _is_validation_like_name(first.component_function):
        return True
    if _is_validation_like_name(second.component_function):
        return True

    if first.owner_function != second.owner_function:
        return False

    return _has_validation_call_between(
        graph,
        first.owner_function,
        first.report_location.line,
        second.report_location.line,
    )


def _parameter_pair_confidence(
    graph: AnalysisGraph,
    first: _ParameterSite,
    second: _ParameterSite,
) -> SiteConfidence:
    """Assign coarse confidence to a disagreeing parameter-site pair."""
    weaker_rank = min(_confidence_rank(first.confidence), _confidence_rank(second.confidence))
    if weaker_rank <= _confidence_rank(SiteConfidence.LOW):
        return SiteConfidence.LOW

    if first.policy.policy_kind == "variant_policy" or second.policy.policy_kind == "variant_policy":
        if first.owner_function == second.owner_function and first.site_kind == second.site_kind:
            return SiteConfidence.MEDIUM
        return SiteConfidence.HIGH

    if _parameter_pair_has_role_signal(graph, first, second):
        return SiteConfidence.HIGH

    return SiteConfidence.MEDIUM


def _build_parameter_site_pairs(
    graph: AnalysisGraph,
    sites: list[_ParameterSite],
    handler: str,
) -> list[_ParameterSitePair]:
    """Pair parameter-family sites whose policies disagree."""
    pairs: list[_ParameterSitePair] = []

    for index, first in enumerate(sites):
        for second in sites[index + 1 :]:
            if _same_parameter_site_identity(first, second):
                continue
            if first.policy.identity() == second.policy.identity():
                continue

            has_variant_policy = (
                first.policy.policy_kind == "variant_policy"
                or second.policy.policy_kind == "variant_policy"
            )
            if not has_variant_policy and not _parameter_pair_has_role_signal(
                graph,
                first,
                second,
            ):
                continue

            pairs.append(
                _ParameterSitePair(
                    first=first,
                    second=second,
                    confidence=_parameter_pair_confidence(graph, first, second),
                )
            )

    pairs.sort(key=lambda pair: pair.sort_key(handler))
    return pairs
