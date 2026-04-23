"""Rich-formatted output for findings and analysis results."""

from __future__ import annotations

from ..models import AccessorKind, Finding, InputAccessFact, Severity


def format_finding(finding: Finding, verbose: bool = False) -> str:
    """Format a single finding as a human-readable string."""
    lines = []
    sev = finding.severity.value.upper()
    lines.append(f"[{sev}] {finding.rule_id}: {finding.title}")
    lines.append(f"  Location: {finding.location}")

    if finding.endpoint:
        methods = ", ".join(finding.endpoint.methods)
        lines.append(f"  Endpoint: {methods} {finding.endpoint.rule or '?'} ({finding.endpoint.handler_qualname})")

    lines.append(f"  {finding.description}")

    if verbose and finding.evidence:
        lines.append("  Evidence:")
        for ev in finding.evidence:
            if isinstance(ev, InputAccessFact):
                if ev.accessor == AccessorKind.DIRECT:
                    key_repr = f"({ev.key_literal})" if ev.key_literal else ""
                    lines.append(
                        f"    - {ev.source.value}{key_repr} "
                        f"at {ev.location} in {ev.function_qualname}"
                    )
                else:
                    lines.append(
                        f"    - {ev.source.value}.{ev.accessor.value}('{ev.key_literal or ev.key_expr or '?'}') "
                        f"at {ev.location} in {ev.function_qualname}"
                    )
            else:
                lines.append(f"    - {ev.raw_code} at {ev.location}")

    return "\n".join(lines)


def format_findings(findings: list[Finding], verbose: bool = False) -> str:
    """Format all findings as a human-readable report."""
    if not findings:
        return "No findings."

    by_severity = {s: [] for s in Severity}
    for f in findings:
        by_severity[f.severity].append(f)

    lines = []
    lines.append(f"Found {len(findings)} potential confusion vulnerabilities:\n")

    for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
        sev_findings = by_severity[sev]
        if not sev_findings:
            continue
        for f in sev_findings:
            lines.append(format_finding(f, verbose=verbose))
            lines.append("")

    summary = {s.value: len(fs) for s, fs in by_severity.items() if fs}
    lines.append(f"Summary: {summary}")

    return "\n".join(lines)
