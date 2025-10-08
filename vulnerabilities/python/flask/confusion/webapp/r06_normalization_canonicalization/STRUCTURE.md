# Normalization-Canonicalization Structure

This directory contains vulnerability examples (1-4) demonstrating canonicalization and normalization issues in Flask applications.

## Directory Structure

```
normalization-canonicalization/
├── routes.py                               # Main coordinator blueprint
├── readme.yml                              # Documentation template
├── __init__.py                             # Python package marker
├── http/                                   # HTTP exploit demonstrations
│   ├── exploit-1.http
│   ├── exploit-2.http
│   ├── exploit-3.http
│   └── exploit-4.http
├── e01_lowercase/                          # Example 1: Lowercase Normalization
│   ├── __init__.py
│   ├── routes.py
│   ├── decorator.py
│   └── database.py
├── e02_insensitive_object_retrieval/       # Example 2: Case-insensitive retrieval
│   ├── __init__.py
│   ├── routes.py
│   ├── decorator.py
│   └── database.py
├── e03_strip_replace_mismatch/             # Example 3: Strip vs Replace mismatch
│   ├── __init__.py
│   ├── routes.py
│   ├── decorator.py
│   └── database/
└── e04_pydantic_strip_bypass/              # Example 4: Pydantic auto-stripping bypass
    ├── __init__.py
    ├── routes.py
    ├── decorator.py
    └── database/
```

## Architecture

### Main Routes.py

The main `routes.py` creates a parent blueprint `normalization_canonicalization` and registers four child blueprints from the subdirectories:

- `lowercase_bp` (e01)
- `lowercase_2_bp` (e02)
- `whitespace_bp` (e03)
- `whitespace_bp_2` (e04)

### Subdirectories

Each subdirectory follows the Flask blueprint pattern:

- **routes.py**: Defines the route handlers with `@unsafe` annotations
- **decorator.py**: Contains authentication and authorization decorators
- **database.py or database/**: Mock database implementations

### URL Structure

Examples are accessible at:

- `/ii/normalization-canonicalization/example1/...`
- `/ii/normalization-canonicalization/example2/...`
- `/ii/normalization-canonicalization/example3/...`
- `/ii/normalization-canonicalization/example4/...`
