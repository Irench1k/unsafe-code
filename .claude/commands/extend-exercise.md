---
description: "Add next exercise to current section with full pipeline (design → code → specs → demos)"
---

# Extend Exercise: $ARGUMENTS

Add the next exercise version to the specified section.

## Before Starting

1. Load `AGENTS.md` for invariants
2. Load `docs/ai/runbooks.md` for workflow
3. Read section README to understand planned evolution

## Workflow

Use `uc-maintainer` to orchestrate, or follow this sequence:

### Step 1: Design
Delegate to **uc-vulnerability-designer**:
- Read section README
- Design: What vuln is fixed from previous? What new vuln introduced?
- Output: Design spec with attack chain, character mapping, business impact

### Step 2: Implement
Delegate to **uc-code-crafter**:
- Clone previous exercise directory
- Implement design spec
- Add @unsafe annotations
- Maintain backward compatibility (unless README says otherwise)

### Step 3: Specs
1. **uc-spec-sync**: Update spec.yml with new version, run ucsync
2. **uc-spec-author**: Create specs for new endpoints/behavior
3. **uc-spec-runner**: Run uctest until green

### Step 4: Demos
Delegate to **uc-exploit-narrator**:
- Create .exploit.http (demonstrates vuln)
- Create .fixed.http (shows fix works)
- Follow character rules from AGENTS.md
- ONE assert per test

### Step 5: Docs
1. `uv run docs generate --target [path]`
2. **uc-docs-editor**: Polish README if needed

### Step 6: Finalize
Delegate to **commit-agent**:
- Run full verification
- Commit with descriptive message

## Quality Checks

Before completing, verify:
- [ ] Section README describes this exercise's goals?
- [ ] ONE new concept only?
- [ ] Vuln is exploitable, fix works?
- [ ] Specs inherit maximally from previous version?
- [ ] Character logic sound in demos?
- [ ] Business impact clear and varied?
