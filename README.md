# Unsafe Code Lab

**Unsafe Code Lab** is a hands-on security training ground for code reviewers and penetration testers. Learn to spot vulnerabilities in production-quality code by understanding *why* they happen: refactoring drift, framework design patterns, and subtle API misuse in modern web frameworks like Flask, Django, FastAPI, and Express.js.                                               
                                                                                                                                        
## Who this is for                                                                                                     
  - *AppSec students* with CTF/bug bounty/pentesting experience who want to master secure code review of real-world web frameworks    
  - *Senior security engineers* needing quick reference material when reviewing code in unfamiliar languages or frameworks            

To get an idea of what this project is all about, we recommend to start with the [Confusion vulnerabilities](vulnerabilities/python/flask/README.md) in Flask:

1. [Source Precedence](vulnerabilities/python/flask/confusion/webapp/r01_source_precedence/README.md) — Different components pull the "same" logical parameter from different places (path vs. query vs. body vs. headers vs. cookies), leading to precedence conflicts, merging issues, or source pollution.
2. [Cross-Component Parse](vulnerabilities/python/flask/confusion/webapp/r02_cross_component_parse/README.md) — Middleware, decorators, or framework helpers parse or reshape inputs in ways that differ from what the view sees.
3. [Authorization Binding](vulnerabilities/python/flask/confusion/webapp/r03_authz_binding/README.md) — Authorization checks identity or value X, but the handler acts on identity or value Y.
4. [HTTP Semantics](vulnerabilities/python/flask/confusion/webapp/r04_http_semantics/README.md) — Wrong assumptions about HTTP methods or content types (e.g., GET with body, form vs. JSON) cause components to read different sources.
5. [Multi-Value Semantics](vulnerabilities/python/flask/confusion/webapp/r05_multi_value_semantics/README.md) — One component treats a parameter as a list while another grabs only the first value, or `.get()` vs `.getlist()` disagreements create different effective values.
6. [Normalization & Canonicalization](vulnerabilities/python/flask/confusion/webapp/r06_normalization_canonicalization/README.md) — Case folding, whitespace stripping, URL decoding, or path normalization makes "equal" values diverge when checked versus used.

## What You'll Find Inside

- **Real code patterns:** See how refactoring and feature additions introduce vulnerabilities.
- **Focus on API Design:** See firsthand how framework API design can either create security traps or completely prevent mistakes that are common elsewhere.
- **Easy Setup:** Execute exploits directly from VSCode using .http files with no Burp or ZAP required.

## Supported Frameworks

**Flask** is our model framework with complete vulnerability coverage.

We're actively expanding coverage to include:

| Language       | Planned Frameworks                                              |
| -------------- | --------------------------------------------------------------- |
| **Python**     | Django, Django REST Framework, FastAPI, CherryPy, Bottle       |
| **JavaScript** | Express.js, Koa, Meteor.js, Nest.js                   |

**Want to help?** We're looking for contributors to help build vulnerability examples for these frameworks. Each framework needs runnable applications demonstrating security pitfalls in production-quality code. Check out the Flask examples to see what we're aiming for, then see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute!

## Two Ways to Learn

### Browse on GitHub (no setup required)
Click through the auto-generated READMEs to learn vulnerabilities, see code snippets, and read exploitation examples. The entire lab works as a self-contained wiki.

Not sure where to start? Go [here](vulnerabilities/python/flask/README.md).

### Run Locally (Docker + VSCode)
Clone the repo, start Docker Compose, and execute exploits from .http files directly in VSCode using the REST Client extension. No pentesting tools required.

#### Prerequisites and Setup

- Install Docker (Docker Desktop or Docker Engine with Compose v2)
- Install [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension for VS Code to execute exploit examples (like `exploit-19.http`) found in `/http/` directories
- Clone this repository:

```bash
git clone https://github.com/Irench1k/unsafe-code
cd unsafe-code
```

**Contributors:** See [CONTRIBUTING.md](CONTRIBUTING.md) for additional setup including `uv` and the documentation generator.

#### Quick Start

You can easily play around with the examples using these commands:
```bash
cd vulnerabilities/python/flask/confusion
docker compose up -d   
```

Open any .http file in VSCode (with [REST Client extension](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)) and click "Send Request" to execute exploits.

- View logs: `docker compose logs -f`
- Stop: `docker compose down`

