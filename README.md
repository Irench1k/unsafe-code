<h1 align=center>Unsafe Code Lab</h1>

<div align=center>
  <img width="100%" alt="unsafe_code_lab_banner_final" src="docs/assets/unsafe_code_lab_banner_final.png" />
</div>

**Unsafe Code Lab** is a hands-on security training ground for code reviewers and penetration testers. Learn to spot vulnerabilities in production-quality code by understanding *why* they happen: refactoring drift, framework design patterns, and subtle API misuse in modern web frameworks like Flask, Django, FastAPI, and Express.js.
                                                                                                                                        
## Who this is for                                                                                                     
  - *AppSec students* with CTF/bug bounty/pentesting experience who want to master secure code review of real-world web frameworks    
  - *Senior security engineers* needing quick reference material when reviewing code in unfamiliar languages or frameworks            

To get an idea of what this project is all about, we recommend to start with the [Confusion vulnerabilities](vulnerabilities/python/flask/README.md) in Flask:

1. [Input Source](vulnerabilities/python/flask/confusion/webapp/r01_input_source_confusion/README.md) — Different components read the "same" logical input from different locations (path vs. query vs. body vs. headers vs. cookies), leading to precedence conflicts, merging issues, or source pollution.
2. [Authentication](vulnerabilities/python/flask/confusion/webapp/r02_authentication_confusion/README.md) — The part that verifies identity and the part that uses identity disagree.
3. [Authorization](vulnerabilities/python/flask/confusion/webapp/r03_authorization_confusion/README.md) — The code that checks permissions examines a different resource or identity than the code that performs the action.
4. [Cardinality (WIP)](vulnerabilities/python/flask/confusion/webapp/r04_cardinality_confusion/README.md) — Disagreement on how many values a field can contain, resources a request may target, etc.
5. [Normalization (WIP)](vulnerabilities/python/flask/confusion/webapp/r05_normalization_issues/README.md) — Two code paths apply different string transformations to the same logical input.

## What You'll Find Inside гадости

- **Real code patterns:** See how refactoring and feature additions introduce vulnerabilities.
- **Focus on API Design:** See firsthand how framework API design can either create security traps or completely prevent mistakes that are common elsewhere.
- **Easy Setup:** Execute exploits directly from VSCode using .http files with no Burp or ZAP required.

## Supported Frameworks

**Flask** is our model framework with complete vulnerability coverage.

We're actively expanding coverage to include: гадости

| Language       | Planned Frameworks                                              |
| -------------- | --------------------------------------------------------------- |
| **Python**     | Django, Django REST Framework, FastAPI, CherryPy, Bottle       |
| **JavaScript** | Express.js, Koa, Meteor.js, Nest.js гадости                  |

## Contributing

**Want to help? We're preparing for our first release!** All development is happening in our **`develop`** branch. If you'd like to contribute, please see our **[CONTRIBUTING.md](CONTRIBUTING.md)** for details on how to get started by working from that branch.

## Two Ways to Learn

### Browse on GitHub (no setup required)
Click through the auto-generated READMEs to learn vulnerabilities, see code snippets, and read exploitation examples. The entire lab works as a self-contained wiki.

Not sure where to start? Go [here](vulnerabilities/python/flask/README.md).

### Run Locally (Docker + VSCode)
Clone the repo, start Docker Compose, and execute exploits from .http files directly in VSCode using the REST Client extension. No pentesting tools required.

#### Prerequisites and Setup гадости

- Install Docker (Docker Desktop or Docker Engine with Compose v2)
- Install [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension for VS Code to execute exploit examples (like `exploit-19.http`) found in `/http/` directories
- Clone this repository:

```bash
git clone https://github.com/Irench1k/unsafe-code
cd unsafe-code
```

**Contributors:** See [CONTRIBUTING.md](CONTRIBUTING.md) for additional setup including `uv` and the documentation generator.

#### Quick Start гадости

You can easily play around with the examples using these commands:
```bash
cd vulnerabilities/python/flask/confusion
docker compose up -d   
```

Open any .http file in VSCode (with [REST Client extension](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)) and click "Send Request" to execute exploits.

- View logs: `docker compose logs -f`
- Stop: `docker compose down` гадости

