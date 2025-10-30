# CherryPy REST API Example

A CherryPy application demonstrating RESTful web services using HTTP method dispatching and session management.

## Quick Start

```bash
cd foundations/python/cherrypy/rest-api
docker compose up -d

# Test the REST API endpoints
curl -X POST http://localhost:8000/ -d "length=12"      # Create/generate string
curl -X GET http://localhost:8000/                      # Retrieve current string
curl -X PUT http://localhost:8000/ -d "another_string=hello"  # Update string
curl -X DELETE http://localhost:8000/                   # Delete string

# Stop and clean up
docker compose down
```

## What This Demonstrates

This example showcases **RESTful API patterns in CherryPy**:

- ✅ **HTTP Method Dispatching** - Route based on HTTP verbs (GET, POST, PUT, DELETE)
- ✅ **Session Management** - Persistent data storage across requests
- ✅ **Content Type Headers** - Proper API response formatting
- ✅ **Method-based Architecture** - Clean separation of CRUD operations

## API Endpoints

### String Generator Service

| Method   | Endpoint | Parameters                  | Description                          |
| -------- | -------- | --------------------------- | ------------------------------------ |
| `GET`    | `/`      | -                           | Retrieve current string from session |
| `POST`   | `/`      | `length=8` (optional)       | Generate new random string           |
| `PUT`    | `/`      | `another_string` (required) | Replace current string               |
| `DELETE` | `/`      | -                           | Remove string from session           |

## Key Features

### Method Dispatcher

Uses `cherrypy.dispatch.MethodDispatcher()` to route HTTP methods to class methods:

```python
API_CONFIG = {
    '/': {
        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        'tools.sessions.on': True,
        'tools.response_headers.headers': [('Content-Type', 'text/plain')],
    }
}
```

### Session State

Maintains server-side sessions to store strings between requests:

- Automatic session cookie management
- Persistent data storage per client
- Clean session cleanup on DELETE

## When to Use This Pattern

Use method dispatching for:

- **RESTful APIs** with clear CRUD operations
- **Resource-oriented services** where HTTP verbs map to actions
- **Stateful applications** requiring session management
- **API endpoints** with consistent response formats

## Alternative Approaches

For different routing needs, consider:

- **Basic routing** (`@cherrypy.expose`) - See `cherrypy/basic`
- **Custom dispatch** (`_cp_dispatch`) - See `cherrypy/dispatch`
