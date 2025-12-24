# Unsafe Code Lab

> Learn to spot real-world vulnerabilities in production-quality code.

## Quick Start

```bash
git clone https://github.com/Irench1k/unsafe-code
cd unsafe-code/flask-confusion
docker compose up -d
```

Then open any `.http` file in VSCode with the [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) extension.

## What's Inside

**[Flask Confusion Vulnerabilities](flask-confusion/)** — A progressive curriculum exploring how different parts of an application can "disagree" about the same data:

| Section | Focus |
|---------|-------|
| [Input Source](flask-confusion/webapp/r01_input_source_confusion/) | Where does the data come from? |
| [Authentication](flask-confusion/webapp/r02_authentication_confusion/) | Who is making the request? |
| [Authorization](flask-confusion/webapp/r03_authorization_confusion/) | What are they allowed to do? |
| [Cardinality](flask-confusion/webapp/r04_cardinality_confusion/) | How many values? How many resources? |
| [Normalization](flask-confusion/webapp/r05_normalization_issues/) | Are these two strings "equal"? |

Each section contains multiple exercises with:
- Realistic vulnerable code (not CTF puzzles)
- Interactive `.http` demos showing the exploit
- Fixed versions demonstrating the secure pattern

## Target Audience

- **Developers** learning secure coding practices
- **AppSec engineers** preparing training materials
- **Students** with CTF/pentesting experience moving to code review

## Contributing

Development happens on the [`develop`](https://github.com/Irench1k/unsafe-code/tree/develop) branch. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the terms in [LICENSE](LICENSE).
