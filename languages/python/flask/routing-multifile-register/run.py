import os
from webapp import app

if __name__ == "__main__":
    # Get configuration from environment variables with sensible defaults
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", 8000))
    # Enable Flask's built-in auto-reloader in development when requested
    debug = os.environ.get("DEV_RELOAD", "0") == "1"

    app.run(host=host, port=port, debug=debug)
