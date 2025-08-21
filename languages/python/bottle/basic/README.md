# Bottle Basic Example

A basic Bottle application demonstrating common web API patterns and security vulnerabilities. Built with [Bottle](https://bottlepy.org/).

## Quick Start

```bash
cd languages/python/bottle/basic
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
```

The `app.py` file provides a consistent interface across all frameworks while maintaining full Bottle compatibility.
