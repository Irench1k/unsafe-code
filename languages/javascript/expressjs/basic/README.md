# Express.js Basic Example

A basic Express.js application demonstrating common web API patterns and security vulnerabilities. Built with [Express.js](https://expressjs.com/).

## Quick Start

```bash
cd languages/javascript/expressjs/basic
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

## Project Structure

This example follows a standardized structure:

```
src/
├── app.ts              # Main application file with standardized entry point
├── controllers/
│   └── index.ts        # Controller for handling routes
├── routes/
│   └── index.ts        # Route definitions
└── types/
    └── index.ts        # Type definitions
package.json           # Node.js dependencies and scripts
Dockerfile            # Container configuration
compose.yml           # Docker Compose production configuration
compose.dev.yml       # Docker Compose development overrides
.dockerignore         # Files to ignore in Docker
tsconfig.json         # TypeScript configuration
```

The `src/app.ts` file provides a consistent interface across all frameworks while maintaining full Express.js compatibility.

## Development Setup

For development with hot-reload and debug logs:

```bash
# Using docker compose with dev overrides
docker compose -f compose.yml -f compose.dev.yml up -d
```
