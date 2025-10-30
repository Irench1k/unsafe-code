# CherryPy Custom Dispatch Example

A CherryPy application demonstrating advanced routing with custom dispatch methods and controller-based architecture.

## Quick Start

```bash
cd foundations/python/cherrypy/dispatch
docker compose up -d

# Test the custom routing patterns
curl http://localhost:8000/user/
curl http://localhost:8000/user/irina
curl http://localhost:8000/user/123
curl http://localhost:8000/user/irina/123

# Stop and clean up
docker compose down
```

## What This Demonstrates

This example showcases **advanced CherryPy routing patterns**:

- ✅ **Custom `_cp_dispatch` method** - Handle complex URL patterns programmatically
- ✅ **Controller-based architecture** - Organize related routes in controller classes
- ✅ **Dynamic route resolution** - Parse URLs and determine appropriate handlers at runtime
- ✅ **Parameter injection** - Modify request parameters during dispatch

## Key Features

### Custom Dispatch Method

The `UserController._cp_dispatch()` method handles complex routing logic:

- `/user/irina/123` → Extracts username and user_id, routes to `details()`
- `/user/irina` → Detects string, routes to `by_name()`
- `/user/123` → Detects number, routes to `by_id()`

### Controller Architecture

Routes are organized in logical controllers:

- `UserController` - Handles all user-related endpoints
- `WebApp` - Main application controller with root routes

## When to Use This Pattern

Use custom dispatch when you need:

- **Complex URL parsing** that exceeds CherryPy's built-in routing
- **Dynamic route resolution** based on parameter types or values
- **RESTful patterns** with consistent URL structures
- **Legacy URL compatibility** when migrating from other systems

## Alternative Approaches

For simpler routing needs, consider:

- **Basic routing** (`@cherrypy.expose`) - See `cherrypy/basic`
- **RESTful APIs** (`MethodDispatcher`) - See `cherrypy/rest-api`
