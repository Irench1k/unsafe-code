# Unsafe Code Lab: Annotation System Design

This document defines the complete annotation system for Unsafe Code Lab, providing a language-agnostic approach to documenting web framework features and vulnerabilities directly in source code.

## Overview

The annotation system enables:

- **Source-proximal documentation**: Keep examples and explanations close to code
- **Automated index generation**: Generate markdown docs and JSON indices
- **GitHub line linking**: Direct links to relevant code sections
- **Multi-scope flexibility**: Annotate functions, code blocks, files, or multi-file patterns
- **Language independence**: Works across Python, JavaScript, Java, and more
- **Future web app support**: Structured data for interactive experiences

## Core Annotation Syntax

### Basic Structure

```yaml
# @unsafe[scope]
# id: framework-type-category-subcategory-001
# title: "Human-readable title"
# category: category.subcategory
# [optional fields...]
# @/unsafe
```

### Mandatory Fields

- **`id`**: Globally unique identifier following pattern `{framework}-{type}-{category}-{subcategory}-{number}`
- **`title`**: Concise, human-readable description
- **`category`**: References hierarchical taxonomy (e.g., `routing.parametric`, `confusion.parameter-source`)

### Optional Fields

- **`complexity`**: One of `1-hop`, `2-hop`, `3-hop`, `advanced` (default: `1-hop`)
- **`lines`**: Number of lines (e.g. `5`) or specific line range for block scope (e.g., `45-67`) - counting from the end of the comment
- **`files`**: Array of related files for multi-file scope
- **`tags`**: Flexible tags for searching and filtering
- **`notes`**: Brief description of what makes this example unique
- **`impact`**: For vulnerabilities (e.g., `["privilege-escalation", "rce"]`)
- **`cwe`**: CWE references for vulnerabilities
- **`owasp`**: OWASP Top 10 mappings

## Scope Types

### Function Scope (`@unsafe[function]`)

Annotates a single function or method. Most common for basic examples.

```python
# @unsafe[function]
# id: flask-vuln-confusion-parameter-source-001
# title: "Parameter Source Confusion with request.values"
# category: confusion.parameter-source
# complexity: 1-hop
# impact: ["privilege-escalation"]
# notes: |
#   Query parameters can override POST form data when using request.values.
#   This specific example shows admin privilege escalation.
# @/unsafe
@app.route("/vuln/parameter-source", methods=["POST"])
def vuln_parameter_source_confusion():
    is_admin = request.values.get('is_admin', 'false').lower() == 'true'
    return f"Admin status: {is_admin}"
```

### Block Scope (`@unsafe[block]`)

Annotates a specific section of code within a larger function or file.

```python
# @unsafe[block]
# id: flask-demo-routing-autodiscovery-001
# title: "Auto-discovery Route Registration Pattern"
# category: routing.autodiscovery
# complexity: 2-hop
# lines: 31-52
# notes: |
#   Demonstrates pkgutil-based route discovery. The key insight is the
#   two-phase registration (blueprint vs function approach).
# @/unsafe
for _finder, name, ispkg in pkgutil.iter_modules(webapp.__path__):
    if not ispkg:
        continue

    try:
        routes_module = importlib.import_module(f'webapp.{name}.routes')
    except ModuleNotFoundError:
        continue

    # Two registration patterns supported
    if hasattr(routes_module, 'bp'):
        app.register_blueprint(routes_module.bp)
        print(f"✓ Registered blueprint from {name}.routes")

    elif hasattr(routes_module, 'register'):
        routes_module.register(app)
        print(f"✓ Registered routes from {name}.routes using register()")
# @/unsafe
```

### File Scope (`@unsafe[file]`)

Annotates an entire file or the main concept it demonstrates.

```python
# @unsafe[file]
# id: flask-demo-routing-registration-patterns-001
# title: "Function-based vs Decorator-based Route Registration"
# category: routing.registration-patterns
# complexity: 1-hop
# files: ["webapp/users/routes.py", "webapp/posts/routes.py"]
# notes: |
#   Contrasts two route registration approaches. users/ shows function-based
#   with explicit app.add_url_rule(), posts/ shows decorator-based.
# @/unsafe
```

### Multi-file Scope (`@unsafe[multifile]`)

Annotates patterns that span multiple files and require understanding their interaction.

```python
# @unsafe[multifile]
# id: flask-demo-routing-multifile-autodiscovery-001
# title: "Complete Auto-discovery Routing Architecture"
# category: routing.autodiscovery
# complexity: 3-hop
# files: ["webapp/__init__.py", "webapp/users/routes.py", "webapp/posts/routes.py"]
# notes: |
#   Full pattern showing auto-discovery setup in __init__.py plus
#   the actual route modules it discovers. Shows both blueprint and
#   function registration styles working together.
# @/unsafe
```

## Hierarchical Metadata System

### Global Taxonomy (`/meta.yml`)

Defines universal categories that apply to all frameworks.

```yaml
# Universal taxonomy - applies to all frameworks
taxonomy:
  features:
    routing:
      name: "Routing & URL Handling"
      description: |
        How frameworks map incoming requests to handler code. This includes
        static routes, dynamic parameters, route constraints, and registration patterns.
      subcategories:
        basic:
          name: "Basic Route Definition"
          description: "Simple static routes and basic patterns"
        parametric:
          name: "Dynamic Route Parameters"
          description: "URL segments that capture values"
        registration-patterns:
          name: "Route Registration Approaches"
          description: "Different ways to register routes with the framework"
        autodiscovery:
          name: "Automatic Route Discovery"
          description: "Patterns for automatically finding and registering routes"

  vulnerabilities:
    confusion:
      name: "Data Source Confusion"
      description: |
        Vulnerabilities arising from ambiguous handling of data from different sources.
        When frameworks provide multiple ways to access the same data, developers may
        choose the wrong accessor, leading to security issues.
      impact: ["privilege-escalation", "business-logic-bypass"]
      subcategories:
        parameter-source:
          name: "Parameter Source Confusion"
          description: |
            When query parameters, form data, and other sources are merged,
            unexpected precedence can allow attackers to override sensitive values.
          attack_patterns: ["query parameter override", "form data pollution"]
          mitigations:
            [
              "Use specific accessors (request.form, request.args)",
              "Validate parameter sources",
            ]

# Impact definitions (referenced by vulnerabilities)
impacts:
  privilege-escalation:
    name: "Privilege Escalation"
    description: "Gaining higher access levels than intended"
    severity: "high"
  business-logic-bypass:
    name: "Business Logic Bypass"
    description: "Circumventing intended application flow or rules"
    severity: "medium"

# Complexity levels
complexity_levels:
  1-hop:
    name: "Single Component"
    description: "Vulnerability contained within a single function or endpoint"
  2-hop:
    name: "Local Interaction"
    description: "Involves interaction between components in the same file"
  3-hop:
    name: "Module Interaction"
    description: "Requires interaction across multiple files or modules"
  advanced:
    name: "System-wide"
    description: "Complex multi-request or architectural vulnerabilities"
```

### Framework-Specific Extensions (`/languages/python/flask/meta.yml`)

Extends global taxonomy with framework-specific details.

```yaml
# Flask-specific extensions and overrides
framework:
  name: "Flask"
  version: "2.3+"
  documentation: "https://flask.palletsprojects.com/"

# Extend global taxonomy with Flask-specific details
taxonomy:
  vulnerabilities:
    confusion:
      subcategories:
        parameter-source:
          flask_specifics:
            vulnerable_accessors:
              ["request.values", "request.get_json(force=True)"]
            safe_accessors:
              ["request.form", "request.args", "request.get_json()"]
            examples_note: |
              Flask's request.values merges form and query data with query parameters
              taking precedence. This differs from other frameworks.
```

## Complete Taxonomy Reference

### Feature Categories

- **routing/**: URL mapping and route handling

  - `basic`: Static route definitions
  - `parametric`: Dynamic URL parameters
  - `registration-patterns`: Different ways to register routes
  - `autodiscovery`: Automatic route discovery patterns
  - `constraints`: Route validation and constraints

- **data-access/**: Request data handling

  - `query-params`: Query string parameter access
  - `form-data`: POST form data handling
  - `json-parsing`: JSON request body processing
  - `file-uploads`: Multipart file upload handling
  - `headers`: HTTP header access patterns
  - `merged-sources`: Combined data accessors

- **responses/**: Response generation patterns

  - `templates`: Template rendering
  - `json-api`: Structured JSON responses
  - `redirects`: URL redirection patterns
  - `streaming`: Large response handling
  - `error-handling`: Error response formatting

- **middleware/**: Request/response processing

  - `before-request`: Pre-processing hooks
  - `after-request`: Post-processing hooks
  - `error-handlers`: Exception handling
  - `context-management`: Request context patterns

- **auth/**: Authentication and authorization
  - `session-based`: Server-side session handling
  - `token-based`: JWT and token authentication
  - `basic-auth`: HTTP basic authentication
  - `oauth`: OAuth flow implementations

### Vulnerability Categories

- **confusion/**: Ambiguous data source handling

  - `parameter-source`: Query vs form vs JSON precedence
  - `route-precedence`: Ambiguous route matching order
  - `data-format`: Content-type confusion
  - `middleware-order`: Middleware execution order issues

- **injection/**: Code and command injection

  - `template`: Server-side template injection
  - `code`: Dynamic code execution
  - `command`: Shell command injection
  - `deserialization`: Unsafe object deserialization

- **dos/**: Denial of service vectors

  - `regex`: Regular expression DoS
  - `memory`: Memory exhaustion attacks
  - `cpu`: CPU exhaustion patterns
  - `resource`: Resource exhaustion

- **type-issues/**: Type system weaknesses
  - `coercion`: Unsafe type casting
  - `validation-bypass`: Type validation bypasses
  - `serialization`: Serialization vulnerabilities
  - `array-scalar-confusion`: Array/scalar type confusion

## GitHub Integration

### Generated Documentation Links

The `generate_index.py` script creates GitHub links with automatic line highlighting:

**Function scope:**

```markdown
| Parameter Source Confusion | Query params override POST data | [`app.py#L69-L74`](https://github.com/user/repo/blob/main/languages/python/flask/basic/app.py#L69-L74) |
```

**Block scope:**

```markdown
| Auto-discovery Pattern | pkgutil-based route discovery | [`__init__.py#L31-L52`](https://github.com/user/repo/blob/main/languages/python/flask/routing-multifile-autodiscovery/webapp/__init__.py#L31-L52) |
```

**Multi-file scope:**

```markdown
| Complete Auto-discovery | Full routing architecture | [📁 View Files](https://github.com/user/repo/tree/main/languages/python/flask/routing-multifile-autodiscovery/webapp) ([init](link), [users](link), [posts](link)) |
```

### Generated Index Structure

```json
{
  "framework": "flask",
  "examples": [
    {
      "id": "flask-vuln-confusion-parameter-source-001",
      "title": "Parameter Source Confusion with request.values",
      "type": "vulnerability",
      "category": "confusion.parameter-source",
      "complexity": "1-hop",
      "scope": "function",
      "files": [
        {
          "path": "languages/python/flask/basic/app.py",
          "lines": [69, 74],
          "github_url": "https://github.com/user/repo/blob/main/languages/python/flask/basic/app.py#L69-L74"
        }
      ],
      "impact": ["privilege-escalation"],
      "notes": "Query parameters can override POST form data when using request.values...",
      "category_info": {
        "name": "Parameter Source Confusion",
        "description": "When query parameters, form data...",
        "attack_patterns": ["query parameter override"],
        "mitigations": ["Use specific accessors"]
      }
    }
  ]
}
```

## Developer Experience

### Minimal Required Fields

For quick examples, only three fields are required:

```python
# @unsafe[function]
# id: flask-demo-basic-routing-001
# title: "Static Route Definition"
# category: routing.basic
# @/unsafe
@app.route("/hello")
def hello():
    return "Hello World"
```

### Editor Support

#### VSCode Snippets

**Python snippets** (`python.json`):

```json
{
  "Unsafe Vulnerability Annotation": {
    "prefix": "unsafe-vuln",
    "body": [
      "# @unsafe[function]",
      "# id: ${1:framework}-vuln-${2:category}-${3:subcategory}-${4:001}",
      "# title: \"${5:Vulnerability Title}\"",
      "# category: ${2:category}.${3:subcategory}",
      "# impact: [\"${7:privilege-escalation}\"]",
      "# notes: |",
      "#   ${8:What makes this example unique?}",
      "# @/unsafe"
    ]
  },
  "Unsafe Feature Demo Annotation": {
    "prefix": "unsafe-demo",
    "body": [
      "# @unsafe[function]",
      "# id: ${1:framework}-demo-${2:category}-${3:subcategory}-${4:001}",
      "# title: \"${5:Feature Demo Title}\"",
      "# category: ${2:category}.${3:subcategory}",
      "# notes: |",
      "#   ${7:What this example demonstrates}",
      "# @/unsafe"
    ]
  },
  "Unsafe Block Annotation": {
    "prefix": "unsafe-block",
    "body": [
      "# @unsafe[block]",
      "# id: ${1:framework}-${2:demo|vuln}-${3:category}-${4:subcategory}-${5:001}",
      "# title: \"${6:Code Block Title}\"",
      "# category: ${3:category}.${4:subcategory}",
      "# lines: ${8:start-end}",
      "# notes: |",
      "#   ${9:What this code block shows}",
      "# @/unsafe"
    ]
  },
  "Unsafe Multi-file Annotation": {
    "prefix": "unsafe-multi",
    "body": [
      "# @unsafe[multifile]",
      "# id: ${1:framework}-demo-${2:category}-${3:subcategory}-${4:001}",
      "# title: \"${5:Multi-file Pattern Title}\"",
      "# category: ${2:category}.${3:subcategory}",
      "# files: [\"${7:file1.py}\", \"${8:file2.py}\"]",
      "# notes: |",
      "#   ${9:How files work together}",
      "# @/unsafe"
    ]
  }
}
```

**JavaScript/TypeScript snippets** (`javascript.json`, `typescript.json`):

```json
{
  "Unsafe Vulnerability Annotation": {
    "prefix": "unsafe-vuln",
    "body": [
      "// @unsafe[function]",
      "// id: ${1:framework}-vuln-${2:category}-${3:subcategory}-${4:001}",
      "// title: \"${5:Vulnerability Title}\"",
      "// category: ${2:category}.${3:subcategory}",
      "// impact: [\"${7:privilege-escalation}\"]",
      "// notes: |",
      "//   ${8:What makes this example unique?}",
      "// @/unsafe"
    ]
  },
  "Unsafe Feature Demo Annotation": {
    "prefix": "unsafe-demo",
    "body": [
      "// @unsafe[function]",
      "// id: ${1:framework}-demo-${2:category}-${3:subcategory}-${4:001}",
      "// title: \"${5:Feature Demo Title}\"",
      "// category: ${2:category}.${3:subcategory}",
      "// notes: |",
      "//   ${7:What this example demonstrates}",
      "// @/unsafe"
    ]
  },
  "Unsafe Block Annotation": {
    "prefix": "unsafe-block",
    "body": [
      "// @unsafe[block]",
      "// id: ${1:framework}-${2:demo|vuln}-${3:category}-${4:subcategory}-${5:001}",
      "// title: \"${6:Code Block Title}\"",
      "// category: ${3:category}.${4:subcategory}",
      "// lines: ${8:start-end}",
      "// notes: |",
      "//   ${9:What this code block shows}",
      "// @/unsafe"
    ]
  },
  "Unsafe Multi-file Annotation": {
    "prefix": "unsafe-multi",
    "body": [
      "// @unsafe[multifile]",
      "// id: ${1:framework}-demo-${2:category}-${3:subcategory}-${4:001}",
      "// title: \"${5:Multi-file Pattern Title}\"",
      "// category: ${2:category}.${3:subcategory}",
      "// files: [\"${7:file1.js}\", \"${8:file2.js}\"]",
      "// notes: |",
      "//   ${9:How files work together}",
      "// @/unsafe"
    ]
  }
}
```

**Java/Kotlin snippets** (`java.json`, `kotlin.json`):

```json
{
  "Unsafe Vulnerability Annotation": {
    "prefix": "unsafe-vuln",
    "body": [
      "// @unsafe[function]",
      "// id: ${1:framework}-vuln-${2:category}-${3:subcategory}-${4:001}",
      "// title: \"${5:Vulnerability Title}\"",
      "// category: ${2:category}.${3:subcategory}",
      "// impact: [\"${7:privilege-escalation}\"]",
      "// notes: |",
      "//   ${8:What makes this example unique?}",
      "// @/unsafe"
    ]
  },
  "Unsafe Feature Demo Annotation": {
    "prefix": "unsafe-demo",
    "body": [
      "// @unsafe[function]",
      "// id: ${1:framework}-demo-${2:category}-${3:subcategory}-${4:001}",
      "// title: \"${5:Feature Demo Title}\"",
      "// category: ${2:category}.${3:subcategory}",
      "// notes: |",
      "//   ${7:What this example demonstrates}",
      "// @/unsafe"
    ]
  }
}
```

#### Snippet Installation

**VSCode Setup:**

1. Open VSCode
2. Go to `File` > `Preferences` > `Configure User Snippets`
3. Select the language (e.g., "python", "javascript", "typescript")
4. Paste the appropriate snippet configuration
5. Save and restart VSCode

**Usage:**

- Type `unsafe-vuln` + Tab for vulnerability annotations
- Type `unsafe-demo` + Tab for feature demonstrations
- Type `unsafe-block` + Tab for code block annotations
- Type `unsafe-multi` + Tab for multi-file patterns

#### Other Editors

**Vim/Neovim** (with UltiSnips):

```vim
snippet unsafe-vuln "Unsafe vulnerability annotation"
# @unsafe[function]
# id: ${1:framework}-vuln-${2:category}-${3:subcategory}-${4:001}
# title: "${5:Vulnerability Title}"
# category: ${2}.${3}
# complexity: ${6:1-hop}
# impact: ["${7:privilege-escalation}"]
# notes: |
#   ${8:What makes this example unique?}
# @/unsafe
endsnippet
```

**Emacs** (with yasnippet):

```emacs-lisp
# key: unsafe-vuln
# name: Unsafe vulnerability annotation
# --
# @unsafe[function]
# id: ${1:framework}-vuln-${2:category}-${3:subcategory}-${4:001}
# title: "${5:Vulnerability Title}"
# category: ${2}.${3}
# complexity: ${6:1-hop}
# impact: ["${7:privilege-escalation}"]
# notes: |
#   ${8:What makes this example unique?}
# @/unsafe
```

### Validation Tools

**Pre-commit hook validation:**

- Required fields present
- Valid category references (exist in meta.yml)
- Unique IDs across project
- Line ranges are accurate (for block scope)
- Referenced files exist (for multi-file scope)

**CLI helper commands:**

```bash
# Generate next available ID
./scripts/next_id.py flask vuln confusion parameter-source
# Output: flask-vuln-confusion-parameter-source-002

# Validate annotations in current directory
./scripts/validate_annotations.py languages/python/flask/basic/

# Preview generated documentation
./scripts/generate_index.py --preview languages/python/flask/
```

## Migration Path

### Phase 1: High-Value Examples

1. Start with existing Flask vulnerabilities (highest educational value)
2. Annotate clear, single-function examples first
3. Use minimal required fields initially

### Phase 2: Complex Patterns

1. Add block and multi-file scope annotations
2. Expand to other Python frameworks
3. Develop framework-specific meta.yml files

### Phase 3: Full Coverage

1. Annotate all demo features
2. Add JavaScript/TypeScript frameworks
3. Implement web app integration

### Example Migration

**Current code:**

```python
# This code is vulnerable, such a thing can work: /user?id=123&type=<script>alert(1)</script>
@app.route("/user")
def show_user_with_params():
    user_id = request.args.get("id")
    user_type = request.args.get("type")  # Vulnerable: no escaping
    return f"User ID: {user_id}, User Type: {user_type}, Route: {request.path}"
```

**Annotated version:**

```python
# @unsafe[function]
# id: flask-vuln-injection-xss-001
# title: "XSS via Unescaped Query Parameters"
# category: injection.xss
# complexity: 1-hop
# impact: ["xss"]
# notes: |
#   Direct output of query parameters without escaping allows XSS.
#   Example: /user?type=<script>alert(1)</script>
# @/unsafe
@app.route("/user")
def show_user_with_params():
    user_id = request.args.get("id")
    user_type = request.args.get("type")  # Vulnerable: no escaping
    return f"User ID: {user_id}, User Type: {user_type}, Route: {request.path}"
```

## Implementation Requirements

### Parser Specifications

The `generate_index.py` script must:

1. **Discover**: Find all files with `@unsafe` annotations
2. **Parse**: Extract YAML content between `@unsafe[scope]` and `@/unsafe`
3. **Validate**: Check required fields and references
4. **Merge**: Combine with hierarchical meta.yml data
5. **Generate**: Create markdown and JSON outputs

### Language Support

**Comments formats:**

- Python: `# @unsafe[scope]`
- JavaScript/TypeScript: `// @unsafe[scope]` or `/* @unsafe[scope] */`
- Java/Kotlin: `// @unsafe[scope]` or `/* @unsafe[scope] */`

**Terminator handling:**

- `@/unsafe` is optional
- Parser reads until end of comment block if no terminator
- Multi-line comments use closing comment as implicit terminator

## Summary

This annotation system provides:

- **Language-agnostic** format that works across all target languages
- **Flexible scope** handling (function/block/file/multi-file)
- **GitHub line linking** with automatic highlighting
- **Hierarchical metadata** to eliminate repetition
- **Minimal boilerplate** for contributors
- **Rich generated documentation** for markdown and JSON
- **Future web app compatibility** through structured data
- **Developer-friendly** tooling and validation

The system balances contributor ease-of-use with the rich metadata needed for high-quality educational content, ensuring Unsafe Code Lab can scale across multiple languages and frameworks while maintaining consistency and educational value.
