# CherryPy Examples

A collection of CherryPy applications demonstrating different routing patterns and architectural approaches.

## Examples Overview

| Example                   | Focus          | Key Features                                  |
| ------------------------- | -------------- | --------------------------------------------- |
| **[basic](basic/)**       | Simple routing | `@cherrypy.expose`, basic forms, query params |
| **[dispatch](dispatch/)** | Custom routing | `_cp_dispatch`, controllers, dynamic URLs     |
| **[rest-api](rest-api/)** | RESTful APIs   | Method dispatcher, sessions, HTTP verbs       |

## Getting Started

Each example is self-contained with its own Docker setup:

```bash
# Navigate to any example
cd basic/  # or dispatch/, rest-api/

# Start the application
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

## Example Details

### [Basic Example](basic/)

**Perfect for beginners** - demonstrates fundamental CherryPy concepts:

- Simple `@cherrypy.expose` routing
- HTML forms and form processing
- Query parameter handling
- Basic authentication patterns

```bash
cd basic/
docker compose up -d
curl http://localhost:8000/
```

### [Custom Dispatch Example](dispatch/)

**Advanced routing** - shows custom URL dispatch and controller architecture:

- Custom `_cp_dispatch` method for complex routing
- Controller-based organization
- Dynamic route resolution based on parameter types
- Parameter injection during dispatch

```bash
cd dispatch/
docker compose up -d
curl http://localhost:8000/user/irina/123
```

### [REST API Example](rest-api/)

**RESTful services** - demonstrates HTTP method dispatching and stateful APIs:

- Method dispatcher routing (GET, POST, PUT, DELETE)
- Session management and persistent state
- Content-type headers and API responses
- Resource-oriented service design

```bash
cd rest-api/
docker compose up -d
curl -X POST http://localhost:8000/ -d "length=12"
```

## Architecture Patterns

These examples demonstrate three common CherryPy architectural patterns:

1. **Function-based** (`basic/`) - Simple exposed functions for straightforward applications
2. **Controller-based** (`dispatch/`) - Class-based organization with custom routing logic
3. **Resource-based** (`rest-api/`) - HTTP method dispatching for RESTful APIs

Choose the pattern that best fits your application's complexity and requirements.

## Next Steps

- Start with `basic/` to understand CherryPy fundamentals
- Move to `dispatch/` when you need complex URL patterns
- Use `rest-api/` for building RESTful web services

Each example includes detailed README files with specific usage instructions and architectural explanations.
