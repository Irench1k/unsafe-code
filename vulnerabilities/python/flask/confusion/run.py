import os

from webapp import create_app

app = create_app()

if __name__ == "__main__":
    # Get configuration from environment variables with sensible defaults
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", 8000))

    # Enable Flask's debug mode (including hot-reload) in development
    # The dev-supervisor.py will let Flask's own reloader handle changes,
    # and only restart the process if it crashes
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    app.run(host=host, port=port, debug=debug)
