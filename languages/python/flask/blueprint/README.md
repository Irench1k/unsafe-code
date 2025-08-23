# Flask Basic Example

A Flask application with multi-file routing approach based on [Blueprint](https://flask.palletsprojects.com/en/stable/api/#flask.Blueprint) functionality.

## Quick Start

```bash
cd languages/python/flask/blueprint
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

The `app.py` file provides a consistent interface across all frameworks while maintaining full Flask compatibility.
