# Unsafe Code Lab

**Unsafe Code Lab** is an open-source collection of vulnerable, runnable backend applications built with modern web frameworks. It's designed for security engineers, researchers, and developers to explore how modern frameworks work, what makes them tick, how they break, and most importantly, how to fix them.

## The Problem: Hidden Risks in Modern Frameworks

The security of a web application depends on more than just the framework's built-in protections; it's also shaped by the subtle ways developers can misuse framework APIs. While frameworks like **Next.js**, **Django**, and **FastAPI** provide strong security foundations, they can't prevent all misconfigurations or logical flaws.

**Unsafe Code Lab was created to address this gap.**

## What You'll Find Inside

This project provides a streamlined way to understand the security landscape of modern web development.

- **Runnable Vulnerable Apps:** Each directory contains a minimal, standalone application with a specific, documented vulnerability.
- **Focus on API Design:** See firsthand how framework API design can either create security traps or completely prevent mistakes that are common elsewhere.
- **Research Harness:** Use the runnable scenarios as a harness for advanced vulnerability research and exploit development.

## Use Cases

You can use Unsafe Code Lab to:

- 🚀 **Onboard Quickly:** Get up to speed on the security nuances of an unfamiliar framework or tech stack.
- 🔒 **Perform Better Code Reviews:** Run targeted secure code reviews by using these examples as a reference for what to look for.
- 🔬 **Conduct Security Research:** Analyze how different frameworks handle security-sensitive operations and discover new vulnerabilities.
- 🎓 **Learn & Teach:** Demonstrate common security pitfalls to your team in a practical, hands-on way.

## Supported Frameworks

Our first public release covers ten modern frameworks across Python and JavaScript. Each framework lives in its own directory in this repository.

| Language       | Frameworks                                                      |
| -------------- | --------------------------------------------------------------- |
| **Python**     | Django, Django REST Framework, FastAPI, Flask, CherryPy, Bottle |
| **JavaScript** | Next.js, Express.js, Koa, Meteor.js, Nest.js                    |

_...and more coming soon!_

## Getting Started

Using the lab is simple:

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/unsafe-code-lab.git
    cd unsafe-code
    ```

2.  **Navigate to a scenario:**
    Each framework has its own directory. Choose one you're interested in.

    ```bash
    cd languages/python/fastapi/basic
    ```

3.  **Follow the local README:**
    Each scenario has its own `README.md` with instructions on how to install dependencies, run the application, and exploit the vulnerability.
