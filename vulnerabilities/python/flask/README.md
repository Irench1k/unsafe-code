# Flask Applications

[Flask](https://flask.palletsprojects.com/) is a lightweight WSGI web application framework in Python. It's designed to be simple and easy to use, making it a popular choice for building web applications and APIs.

This collection demonstrates how security vulnerabilities emerge in Flask applications through realistic development patterns: framework-specific behaviors, common architectural decisions, and subtle interactions between components.

## Confusion & Inconsistent Interpretation

Inconsistent interpretation happens when code that should be working with **one logical input value** ends up consulting **different representations or different sources** of that value. Sometimes this means security checks and business logic read from entirely different places (path vs. query vs. body vs. a merged helper). Other times, both read the same source but one normalizes, casts, or handles multiple values differently than the other. Either way, the result is the same: two effective values for what should be a single input, opening the door to authorization bypasses, identity confusion, and data integrity violations.

1. [Input Source](vulnerabilities/python/flask/confusion/webapp/r01_input_source_confusion/README.md) — Different components read the "same" logical input from different locations (path vs. query vs. body vs. headers vs. cookies), leading to precedence conflicts, merging issues, or source pollution.
2. [Authentication](vulnerabilities/python/flask/confusion/webapp/r02_authentication_confusion/README.md) — The part that verifies identity and the part that uses identity disagree.
3. [Authorization](vulnerabilities/python/flask/confusion/webapp/r03_authorization_confusion/README.md) — The code that checks permissions examines a different resource or identity than the code that performs the action.
4. [Cardinality (WIP)](vulnerabilities/python/flask/confusion/webapp/r04_cardinality_confusion/README.md) — Disagreement on how many values a field can contain, resources a request may target, etc.
5. [Normalization (WIP)](vulnerabilities/python/flask/confusion/webapp/r05_normalization_issues/README.md) — Two code paths apply different string transformations to the same logical input.

### Running the examples

First, navigate to the [`confusion`](confusion/README.md) directory, and then use Docker Compose:

```bash
cd vulnerabilities/python/flask/confusion
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```
The application will be available at `http://localhost:8000`.

### How to spot it
- Pick a logical input (like `user_id` or `resource_name`) and trace its **full lifecycle**: where it enters the system, how it's merged or combined with other sources, what normalizations or casts happen, and where it's ultimately accessed.
- Compare what the **security check** reads versus what the **business logic** uses, not just the variable name, but the actual source (path? query? body? merged dict? default value?).
- Look for "smart" helpers like `request.values` or custom accessors that merge multiple sources, and check whether all consumers agree on precedence.
- Watch for **multi-value** and **type** handling differences: does one place use `.get()` (first value) while another uses `.getlist()` (all values)? Are there implicit casts or normalization steps (case folding, URL decoding, whitespace stripping)?
- Verify **ordering**: do guards run before or after inputs are finalized, merged, or normalized? Are defaults or fallbacks introduced after the security check?

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Flask Security Considerations](https://flask.palletsprojects.com/en/latest/security/)
- [Flask Extension Registry](https://flask.palletsprojects.com/en/latest/extensions/)
