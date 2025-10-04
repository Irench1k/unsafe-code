# Normalization-Canonicalization Structure

This directory contains vulnerability examples (18-21) demonstrating canonicalization and normalization issues in Flask applications.

## Directory Structure

```
normalization-canonicalization/
├── routes.py                          # Main coordinator blueprint
├── readme.yml                         # Documentation template
├── __init__.py                        # Python package marker
├── http/                              # HTTP exploit demonstrations
│   ├── exploit-18.http
│   ├── exploit-19.http
│   ├── exploit-20.http
│   └── exploit-21.http
├── r01_lowercase/                     # Example 18: Lowercase Normalization
│   ├── __init__.py
│   ├── routes.py
│   ├── decorator.py
│   └── database.py
├── r02_insensitive_object_retrieval/  # Example 19: Case-insensitive retrieval
│   ├── __init__.py
│   ├── routes.py
│   ├── decorator.py
│   └── database.py
├── r03_whitespace/                    # Example 20: Whitespace (strip vs replace)
│   ├── __init__.py
│   ├── routes.py
│   ├── decorator.py
│   └── database/
└── r04_whitespace/                    # Example 21: Whitespace with Pydantic
    ├── __init__.py
    ├── routes.py
    ├── decorator.py
    └── database/
```

## Architecture

### Main Routes.py

The main `routes.py` creates a parent blueprint `normalization_canonicalization` and registers four child blueprints from the subdirectories:

- `lowercase_bp` (r01)
- `lowercase_2_bp` (r02)
- `whitespace_bp` (r03)
- `whitespace_bp_2` (r04)

### Subdirectories

Each subdirectory follows the Flask blueprint pattern:

- **routes.py**: Defines the route handlers with `@unsafe` annotations
- **decorator.py**: Contains authentication and authorization decorators
- **database.py or database/**: Mock database implementations

### URL Structure

Examples are accessible at:

- `/ii/normalization-canonicalization/example18/...`
- `/ii/normalization-canonicalization/example19/...`
- `/ii/normalization-canonicalization/example20/...`
- `/ii/normalization-canonicalization/example21/...`
