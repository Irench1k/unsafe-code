# Confusion & Inconsistent Interpretation

## Running the Examples

All examples in this category share a single Docker Compose environment:

```bash
cd vulnerabilities/python/flask/confusion
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

The application will be available at `http://localhost:8000`.

## Subcategories

1. [Input Source](webapp/r01_input_source_confusion/README.md) — Source precedence bugs occur when different code paths read the "same" logical input from different locations (path vs. query vs. body vs. headers vs. cookies).
2. [Authentication](webapp/r02_authentication_confusion/README.md) — Authentication confusion occurs when the code that **verifies identity** examines a different value than the code that **acts on identity**.
3. [Authorization](webapp/r03_authorization_confusion/README.md) — Authorization confusion happens when the code that **checks permissions** examines a different resource or identity than the code that **performs the action**.
4. [Cardinality](webapp/r04_cardinality_confusion/README.md) — Cardinality confusion occurs when one part of the code treats a parameter as a **single value** while another treats it as a **list**. The parser, validator, and business logic disagree on whether you sent one item or many.
5. [Normalization](webapp/r05_normalization_issues/README.md) — Character normalization confusion happens when two code paths apply **different string transformations** to the same logical input.
