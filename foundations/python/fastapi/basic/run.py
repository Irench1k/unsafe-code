import os

import uvicorn

if __name__ == "__main__":
    # Get configuration from environment variables with sensible defaults
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", 8000))
    # Enable auto-reloader via uvicorn
    debug = os.environ.get("DEV_RELOAD", "0") == "1"

    uvicorn.run("app:app", host=host, port=port, reload=debug)
