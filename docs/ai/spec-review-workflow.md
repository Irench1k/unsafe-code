# Spec Review Workflow (Diff → Demos → Specs)

Single-source, repeatable checklist for reviewing a new exercise version (vNNN): identify externally visible changes, decide whether they are intentional, and translate them into code fixes or inheritable E2E specs. Use this when you receive a new version ID (e.g., v307 or v401) and need to align code, demos, and specs quickly.

---

## 0) Preconditions
- Work in repo root `unsafe-code`.
- Services: `tools/dev/ucdemo` auto-spawns the stack; for deeper debugging use `uclogs` (`docker compose` in `vulnerabilities/python/flask/confusion/compose.yml`).
- Tools on PATH: when wrapper binaries aren’t installed, call the Python/Node entry points explicitly:
  - Diffs: `python tools/ucdiff.py ...`
  - Inheritance: `python tools/ucsync.py vNNN`
  - Specs: `pushd spec && npx uctest vNNN -k && popd`
  - Demos: `tools/dev/ucdemo r0X/eYY --bail -v`

---

## 1) Read & Map Intent (manual first)
1. Curriculum: `docs/confusion_curriculum/r0X_*.md` (section plan) + `docs/confusion_curriculum/endpoint_index.md`.
2. Section README: `vulnerabilities/.../r0X_*/README.md`.
3. Demo intent: skim `http/eYY/*.http` titles/impacts.
4. Note the advertised vuln/fix lifecycle for this exercise and the previous one.

---

## 2) Diff the Code (what actually changed)
Run in repo root:
```bash
python tools/ucdiff.py vNNN           # file-level +/-
python tools/ucdiff.py vNNN -o        # function outline
python tools/ucdiff.py vNNN -r        # routes only
python tools/ucdiff.py vNNN -cF       # focused code (syntax-aware)
```
Record every externally visible change:
- New/modified routes, auth decorators, middleware order
- Request/response shape changes (params, status codes)
- Helpers that read/write request state (`g`, session, tokens)
- Data-layer defaults that surface to API (e.g., new fields)

Classify each as **intentional feature**, **vulnerability surface**, or **drift/bug**.

---

## 3) Run Behavior Probes
1. Regenerate inheritance: `python tools/ucsync.py vNNN`.
2. Specs (from `spec/`): `npx uctest vNNN -k`.
3. Demos: `tools/dev/ucdemo r0X/eYY --bail -v` (exploit + previous fix).
4. Logs on failures: `uclogs --tail=80`.

Note which failures are syntax vs behavior; keep failing tests as signals.

---

## 4) Triage & Decide
For each change spotted in step 2:
- **Planned + missing coverage** → add specs (happy/authn/authz/validation) in vNNN.
- **Unplanned drift that breaks inheritance** → prefer code fix to restore old behavior; only exclude specs when README documents the change.
- **New vuln behavior** → add `vuln-*.http` spec in vNNN; ensure previous vuln spec is excluded/fixed in `spec/spec.yml`.
- **Docs mismatch** → update section README + curriculum text to match chosen behavior (no history lessons).

---

## 5) Write Specs (inheritance-first)
- Keep files tiny and lifecycle-scoped; import canonical `happy.http` where possible.
- Use helpers from `spec/utils.cjs`; avoid reimplementing parsing/assertions.
- New endpoint? Add `happy.http` + `authn.http` + `authz.http` (as needed) and a `vuln-*.http` if demonstrating the exercise vuln.
- Add exclusions in `spec/spec.yml` only when behavior genuinely diverges.
- After edits: `python tools/ucsync.py vNNN` then `pushd spec && npx uctest vNNN -k && popd`.

---

## 6) Verify Demos
- Each `.exploit.http` and `.fixed.http` must have at least one assertion that would fail if the exploit doesn’t work or the fix regresses.
- Prefer a final GET/check that proves the business impact (wrong tenant data, wrong balance, etc.).
- Keep cookie handling minimal; use `seedBalance`/`resetDB` helpers for idempotency.

---

## 7) Finalize & Document
- Rerun: `python tools/ucsync.py vNNN`, `npx uctest vNNN -k`, `tools/dev/ucdemo r0X/eYY --bail -v`.
- Update docs that describe the behavior you just enforced (README + curriculum).
- Record open questions or deliberate exclusions in `spec/spec.yml` comments.

---

## 8) Automation Hooks (optional)
- `python tools/ucdiff.py vNNN --json` → feed into a TODO list for missing specs.
- `find spec/vNNN -name "~*.http"` → see what’s inherited; `find spec/vNNN -name "vuln-*.http"` → current vuln coverage.
- `python tools/ucdiff.py vNNN --check-specs` (if available) to flag code changes without nearby spec edits.

---

## Example: v307 Token Swap Hijack (r03/e07)
- Diff shows new `PATCH /restaurants/<id>` and middleware `send_and_verify_domain_token` running before `require_restaurant_owner`.
- Behavior: first PATCH without token returns `verification_email_sent`; second PATCH with token updates victim restaurant ID from token claims, ignoring path ID → hijack.
- Required coverage: vuln spec (`restaurants/patch/vuln-token-swap-hijack.http`) plus happy/authn/authz specs for the new PATCH route; demo should assert the hijack result.
- Drift spotted: fixed demo currently targets the wrong restaurant and lacks assertions—tighten during next pass.

Use this workflow for any future version; swap vNNN/r0X/eYY as appropriate and keep inheritance maximized.
