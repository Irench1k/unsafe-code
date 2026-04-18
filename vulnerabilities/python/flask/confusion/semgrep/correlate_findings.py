"""
Post-processor for Semgrep confusion vulnerability findings.

This script uses a "Context Bucket" architecture. Individual Semgrep findings
are placed into semantic buckets based on two properties:
  1. The File they belong to (intra-file correlation).
  2. A designated 'correlation_key' from the rule metadata (cross-file correlation).

Buckets are then evaluated for structural preconditions (Tier 2) or known
complementary confusion pairs (Tier 1).

Usage:
    python correlate_findings.py results.json
"""

import json
import sys
import uuid
from collections import defaultdict

# ---------------------------------------------------------------------------
# Configuration: Known Confusion Pairs
# ---------------------------------------------------------------------------
CONFUSION_PAIRS = [
    # Example 1 pair
    (
        "input-source-conditional-precedence",
        "input-source-getlist-or-get-fallback",
        "Input Source Confusion: two components use opposite precedence for single-value vs list extraction.",
    ),
    # Example 2 pairs (All cross-file combinations)
    (
        "input-source-call-with-form",
        "input-source-call-with-values",
        "Input Source Confusion: The same underlying function is called with conflicting request accessors (form vs values).",
    ),
    (
        "input-source-call-with-form",
        "input-source-call-with-args",
        "Input Source Confusion: The same underlying function is called with conflicting request accessors (form vs args).",
    ),
    # Example 3 pair
    (
        "input-source-content-type-branch",
        "input-source-user-data-overlay-merge",
        "Input Source Confusion: content-type polymorphism feeds a mass-assignment overlay merge. User-chosen input shape is spread before a 'safe' overlay, so fields the overlay does not name pass through to the model validator.",
    ),
    # Example 4 pair
    (
        "input-source-or-fallback-chain",
        "input-source-content-type-branch",
        "Input Source Confusion: one component reads a key from an "
        "OR-fallback chain across multiple request sources (args/json/form "
        "with precedence), while another component reads the same key from "
        "only one source chosen by content-type. An attacker populating "
        "multiple channels can cause the two components to observe "
        "different values — useful for bypassing validation that runs on "
        "the OR-chain side.",
    ),
]

# TIER 2: Sets of primitives that, if found in the same context, form a structural precondition
PRIMITIVE_COMBINATIONS = [
    # Example 1: Mixed Single/List access
    (
        {"primitive-dict-get-access", "primitive-dict-getlist-access"},
        "Mixed access methods: component uses both single-value and list-value accessors. "
        "This is a structural precondition for Input Source Confusion.",
    ),
    # Example 2: Mixed Request Accessors (All 3 possible conflicting pairs)
    (
        {"primitive-source-bulk-pass-form", "primitive-source-bulk-pass-values"},
        "Mixed access methods: component uses both isolated (form) and merged (values) sources.",
    ),
    (
        {"primitive-source-bulk-pass-form", "primitive-source-bulk-pass-args"},
        "Mixed access methods: component uses conflicting isolated sources (form vs args).",
    ),
    (
        {"primitive-source-bulk-pass-form", "primitive-source-bulk-pass-json"},
        "Mixed access methods: component uses conflicting isolated sources (form vs json).",
    ),
    (
        {"primitive-source-bulk-pass-values", "primitive-source-bulk-pass-json"},
        "Mixed access methods: component uses both isolated (json) and merged (values) sources.",
    ),
    # Example 3: Mass Assignment (Requires ALL THREE to be flagged!)
    (
        {
            "primitive-bulk-extraction",
            "primitive-dict-unpack-merge",
            "primitive-model-bulk-validation",
        },
        "Mass Assignment Preconditions: The context contains bulk data extraction, dictionary merging, "
        "and model validation. Verify if these mechanisms connect in a single data flow.",
    ),
    # Example 4: Mixed source-access primitives
    (
        {"primitive-source-key-extract-args", "primitive-source-key-extract-form"},
        "Mixed request sources: component accesses both args and form.",
    ),
    (
        {"primitive-source-key-extract-args", "primitive-source-key-extract-json"},
        "Mixed request sources: component accesses both args and json.",
    ),
    (
        {"primitive-source-key-extract-form", "primitive-source-key-extract-json"},
        "Mixed request sources: component accesses both form and json.",
    ),
    (
        {"primitive-source-key-extract-form", "primitive-source-key-extract-values"},
        "Mixed request sources: component accesses both form and values.",
    ),
    (
        {"primitive-source-key-extract-json", "primitive-source-key-extract-values"},
        "Mixed request sources: component accesses both json and values.",
    ),
]


def extract_rule_suffix(check_id: str) -> str:
    return check_id.rsplit(".", 1)[-1]


def clean_metavar(raw: str) -> str:
    tokens = raw.split()
    if tokens and all(t == tokens[0] for t in tokens):
        return tokens[0]
    return raw


def parse_findings(results: dict) -> list[dict]:
    findings = []
    for r in results.get("results", []):
        extra = r.get("extra", {})
        metadata = extra.get("metadata", {})

        metavars = {
            k: clean_metavar(v.get("abstract_content", "").strip())
            for k, v in extra.get("metavars", {}).items()
        }

        findings.append(
            {
                "uid": str(uuid.uuid4()),
                "rule_id": extract_rule_suffix(r["check_id"]),
                "path": r["path"],
                "start_line": r["start"]["line"],
                "end_line": r["end"]["line"],
                "lines": extra.get("lines", "").strip(),
                "severity": extra.get("severity", "WARNING"),
                "correlation_key": metadata.get("correlation_key"),
                "scope": metadata.get("scope"),
                "metavars": metavars,
                "metadata": metadata,
            }
        )
    return findings


def derive_helper_key_bindings(findings: list[dict]) -> dict[str, set]:
    """
    Two-hop correlation step, driven entirely by YAML metadata.
    Does not rely on hardcoded rule IDs.
    """
    helper_names = set()

    # Step 1: Identify the helper definitions
    for f in findings:
        meta = f.get("metadata", {})
        if meta.get("two_hop_role") == "definition":
            helper_var = meta.get("two_hop_helper_metavar")
            # Resolve the metavar (e.g. "$HELPER") to its value (e.g. "get_request_parameter")
            name = f["metavars"].get(helper_var) if helper_var else None
            if name:
                helper_names.add(name)

    helper_to_keys: dict[str, set] = defaultdict(set)

    # Step 2: Correlate call sites
    for f in findings:
        meta = f.get("metadata", {})
        if meta.get("two_hop_role") == "call_site":
            helper_var = meta.get("two_hop_helper_metavar")
            literal_var = meta.get("two_hop_literal_metavar")

            if helper_var and literal_var:
                name = f["metavars"].get(helper_var)
                literal_val = f["metavars"].get(literal_var)

                # If this call is targeting one of our known helpers, extract the key
                if name in helper_names and literal_val:  # noqa: SIM102
                    # Strip both single and double quotes cleanly
                    if literal_val.startswith(("'", '"')) and literal_val.endswith(("'", '"')):
                        clean_literal = literal_val.strip("'\"")
                        helper_to_keys[name].add(clean_literal)

                        # Tag the finding so the Bucketer catches it
                        f["derived_literal_key"] = clean_literal

    return helper_to_keys


def build_contexts(findings: list[dict]) -> dict:
    """
    Assigns findings to logical 'Context Buckets'. A finding can belong to
    multiple buckets simultaneously.
    """
    contexts = defaultdict(list)

    for f in findings:
        # 1. Intra-file bucket (always present).
        contexts[f"File: {f['path']}"].append(f)

        # 2. Cross-file semantic bucket via correlation_key metavariable.
        corr_key = f.get("correlation_key")
        if corr_key and corr_key in f["metavars"]:
            corr_value = f["metavars"][corr_key]
            if corr_value:
                contexts[f"Correlation Key [{corr_key} == '{corr_value}']"].append(f)

        # 3. Codebase-wide bucket for rules tagged scope=codebase.
        if f.get("scope") == "codebase":
            contexts["Codebase: global"].append(f)

        # 4. Derived literal-key bucket (two-hop correlation).
        derived_key = f.get("derived_literal_key")
        if derived_key:
            contexts[f"Literal Key: '{derived_key}'"].append(f)

    return dict(contexts)


def classify_confidence(ctx_label: str) -> tuple[str, int]:
    """
    Assigns confidence and priority based on the bucket type.
    Lower priority number = stronger evidence = reported first.
    """
    if ctx_label.startswith("Correlation Key ["):
        return "HIGH", 1
    if ctx_label.startswith("Literal Key: "):
        return "HIGH", 1
    if ctx_label.startswith("File: "):
        return "MEDIUM", 2
    if ctx_label == "Codebase: global":
        return "LOW", 3
    return "MEDIUM", 2


def correlate_findings(contexts: dict, all_findings: list[dict]) -> tuple[list[dict], list[dict]]:
    candidates = []

    for ctx_label, ctx_findings in contexts.items():
        confidence, priority = classify_confidence(ctx_label)

        rules_in_ctx = defaultdict(list)
        for f in ctx_findings:
            rules_in_ctx[f["rule_id"]].append(f)

        # 1. Tier 1 pairs
        for rule_a, rule_b, desc in CONFUSION_PAIRS:
            if rule_a in rules_in_ctx and rule_b in rules_in_ctx:
                tier1_comps = rules_in_ctx[rule_a] + rules_in_ctx[rule_b]
                candidates.append(
                    {
                        "confidence": confidence,
                        "description": desc,
                        "context_label": ctx_label,
                        "components": tier1_comps,
                        "priority": priority,
                    }
                )

        # 2. Tier 2 primitive combinations (only in file-level buckets —
        #    codebase-global is too weak for primitive-level evidence).
        if not ctx_label.startswith("Codebase:"):
            tier2_only = [f for f in ctx_findings if f["severity"] == "INFO"]
            present_tier2_rules = set(f["rule_id"] for f in tier2_only)

            for required_set, desc in PRIMITIVE_COMBINATIONS:
                if required_set.issubset(present_tier2_rules):
                    tier2_comps = [f for f in tier2_only if f["rule_id"] in required_set]
                    candidates.append(
                        {
                            "confidence": "MEDIUM",
                            "description": desc,
                            "context_label": ctx_label,
                            "components": tier2_comps,
                            "priority": 4,
                        }
                    )

    # Sort: HIGH first, MEDIUM next, LOW last; within each, larger
    # combinations rank higher.
    candidates.sort(key=lambda x: (x["priority"], -len(x["components"])))

    final_results = []
    consumed_uids = set()

    for cand in candidates:
        unconsumed = [f for f in cand["components"] if f["uid"] not in consumed_uids]

        is_valid = False
        if cand["confidence"] in ("HIGH", "LOW"):
            if len({f["rule_id"] for f in unconsumed}) >= 2:
                is_valid = True
        elif cand["confidence"] == "MEDIUM":
            unconsumed_rules = {f["rule_id"] for f in unconsumed}
            # Tier 1 pair at MEDIUM (file-level)
            for rule_a, rule_b, _ in CONFUSION_PAIRS:
                if {rule_a, rule_b}.issubset(unconsumed_rules):
                    is_valid = True
                    break
            # Tier 2 combination at MEDIUM
            if not is_valid:
                for req_set, _ in PRIMITIVE_COMBINATIONS:
                    if req_set.issubset(unconsumed_rules):
                        is_valid = True
                        break

        if is_valid:
            for f in unconsumed:
                consumed_uids.add(f["uid"])
            cand["components"] = unconsumed
            final_results.append(cand)

    unpaired = [
        f for f in all_findings if f["uid"] not in consumed_uids and f["severity"] != "INFO"
    ]

    return final_results, unpaired


def print_report(correlated: list[dict], unpaired: list[dict], total_count: int):
    print("=" * 80)
    print("CONFUSION VULNERABILITY CORRELATION REPORT")
    print("=" * 80)

    high = sum(1 for r in correlated if r["confidence"] == "HIGH")
    medium = sum(1 for r in correlated if r["confidence"] == "MEDIUM")
    low = sum(1 for r in correlated if r["confidence"] == "LOW")

    print(f"\nTotal individual findings: {total_count}")
    print(f"Correlated results:  {high} HIGH  |  {medium} MEDIUM  |  {low} LOW")
    print(f"Unpaired findings:   {len(unpaired)}")

    def print_grouped_components(components):
        grouped = defaultdict(list)
        for c in components:
            key = (c["path"], c["start_line"], c["end_line"], c["lines"])
            grouped[key].append(c["rule_id"])

        sorted_keys = sorted(grouped.keys(), key=lambda x: (x[0], x[1]))
        for path, start_line, end_line, lines in sorted_keys:
            unique_rules = list(dict.fromkeys(grouped[(path, start_line, end_line, lines)]))
            rule_str = ", ".join(unique_rules)
            loc = (
                f"line {start_line}" if start_line == end_line else f"lines {start_line}-{end_line}"
            )
            print(f"    ({path}:{loc}) [{rule_str}]")
            for line in lines.split("\n"):
                print(f"      | {line}")
            print()

    if correlated:
        print("\n" + "-" * 80)
        print("CORRELATED FINDINGS")
        print("-" * 80)

        for i, entry in enumerate(correlated, 1):
            print(f"\n[{i}] [{entry['confidence']}] {entry['description']}")
            print(f"  Matched via: {entry['context_label']}\n")
            print_grouped_components(entry["components"])

    if unpaired:
        print("-" * 80)
        print("UNPAIRED FINDINGS (individual weaknesses, no counterpart)")
        print("-" * 80)
        print_grouped_components(unpaired)

    print("=" * 80)


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <results.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        results = json.load(f)

    findings = parse_findings(results)

    # Two-hop correlation: derive literal keys from helper call sites.
    derive_helper_key_bindings(findings)

    contexts = build_contexts(findings)
    correlated, unpaired = correlate_findings(contexts, findings)
    print_report(correlated, unpaired, len(findings))


if __name__ == "__main__":
    main()
