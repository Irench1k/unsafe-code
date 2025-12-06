# Curriculum & Exercise Structure

Authoritative map of sections, versions, and exercise layout for the Flask confusion tutorial.

---

## Documentation Sources
| Location | Purpose | Authority |
|----------|---------|-----------|
| `docs/confusion_curriculum/` | Master curriculum (language-agnostic) | Authoritative |
| `vulnerabilities/.../webapp/*/README.md` | Flask-specific implementation notes | May lag |

`docs/confusion_curriculum/` contents:
```
README.md
endpoint_index.md
r01_input_source_confusion.md
r02_authentication_confusion.md
r03_authorization_confusion.md
r04_cardinality_confusion.md
r05_normalization_issues.md
```

---

## Sections & Versions
| Section | Directory | Category | Versions |
|---------|-----------|----------|----------|
| r01 | `r01_input_source_confusion` | Input parsing | v100–v108 |
| r02 | `r02_authentication_confusion` | Identity verification | v201–v206 |
| r03 | `r03_authorization_confusion` | Permission checks | v301–v307 |
| r04 | `r04_cardinality_confusion` | Singular vs plural | v401–v405 |
| r05 | `r05_normalization_issues` | String transforms | v501–v509 |

### Version Numbering
```
vXYY
X  = Section number (1–5)
YY = Exercise number (00–09)
```
Examples: v101 (r01/e01), v301 (r03/e01), v307 (r03/e07).

---

## Exercise Directory Layout
```
eNN_exercise_name/
├── __init__.py           # Blueprint registration
├── routes.py             # Flask endpoints (contains @unsafe)
├── auth.py               # Auth logic
├── models.py             # Data models
├── database.py           # Storage layer
├── e2e_helpers.py        # Test endpoints (/e2e/reset, /e2e/balance)
└── utils.py              # Utilities
```

### Blueprint/Route Wiring
App entry (`vulnerabilities/python/flask/confusion/webapp/routes.py`):
```python
from flask import Blueprint
from .r01_input_source_confusion.routes import bp as bp_r01
from .r02_authentication_confusion.routes import bp as bp_r02
from .r03_authorization_confusion.routes import bp as bp_r03

bp = Blueprint("confusion", __name__, url_prefix="/api")
bp.register_blueprint(bp_r01)
bp.register_blueprint(bp_r02)
bp.register_blueprint(bp_r03)
```
Section routing pattern:
```python
from flask import Blueprint
from .e00_baseline.routes import bp as bp_e00
from .e01_dual_parameter.routes import bp as bp_e01

bp = Blueprint("input_source_confusion", __name__)
bp.register_blueprint(bp_e00, url_prefix="v100")
bp.register_blueprint(bp_e01, url_prefix="v101")
```
Exercise routing pattern:
```python
from flask import Blueprint, jsonify, request

bp = Blueprint("e01_dual_params", __name__)

@bp.route("/orders", methods=["POST"])
def create_new_order():
    # Vulnerable code with @unsafe annotation
    ...
```

---

## Demo & Spec Locations
```
# Demos
rNN_section_name/
└── http/
    ├── common/setup.http
    ├── httpyac.config.js
    ├── e00/e00_baseline.http
    ├── eNN/
    │   ├── eNN_name.exploit.http
    │   └── eNN_name.fixed.http

# E2E Specs
spec/
├── spec.yml
├── utils.cjs
├── v201/
│   ├── _imports.http
│   └── {resource}/{method}/*.http
└── v301/
    ├── ~inherited.http (generated)
    └── new-test.http (local)
```

---

## Adding a New Exercise (Lifecycle View)
1. **Copy previous exercise directory** (e.g., `cp -r e06_domain_tokens e07_token_swap`).
2. **Wire blueprint** in section `routes.py` with new `vXYY` prefix.
3. **Update `spec/spec.yml`**: add version entry with `inherits` previous version, tags, and necessary exclusions (for fixed vulns).
4. **Run `ucsync`** to generate inherited specs; run `uctest vXYY/` to verify baseline.
5. **Create demos**: `.exploit.http` and `.fixed.http` (TDD: expect failures first).
6. **Implement vulnerability** with `@unsafe` annotation; rerun demos until exploit passes.
7. **Implement fix**; rerun demos to ensure exploit blocked.
8. **Port behavior to specs**: vuln coverage, new endpoints/fields, happy/validation; add exclusions for fixed vulns.
9. **Diff previous exercise** (`diff -r`) to capture every externally visible change; add specs accordingly.

---

## `@unsafe` Annotation Requirement
```python
# @unsafe {
#     "vuln_id": "v301",
#     "severity": "high",
#     "category": "authorization-confusion",
#     "description": "Decorator checks session but handler uses URL param"
# }
def vulnerable_function():
    ...
```

---

## Core Principles
1. One concept per exercise.
2. Maximize inheritance; overrides/exclusions only for genuine behavior changes.
3. Real SaaS evolution: apps add features, rarely break compatibility.
4. Vulnerabilities are subtle, production-quality.
5. Tests must fail when behavior is missing or broken.
