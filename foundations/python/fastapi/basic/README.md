# FastAPI Basic Example

A basic FastAPI application demonstrating common web API patterns and security vulnerabilities. Built with [FastAPI](https://fastapi.tiangolo.com/).

## Quick Start

```bash
cd foundations/python/fastapi/basic
docker compose up -d

# View logs
docker compose logs -f

# Stop and clean up
docker compose down
```

## Project Structure

This example follows a standardized structure:

```
app.py              # Main application file with standardized entry point
requirements.txt    # Python dependencies
Dockerfile          # Container configuration
templates/          # HTML templates
```

The `app.py` file provides a consistent interface across all frameworks while maintaining full FastAPI compatibility.
