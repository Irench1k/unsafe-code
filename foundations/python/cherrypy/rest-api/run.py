import os

import cherrypy
from app import app, config

if __name__ == "__main__":
    # Get configuration from environment variables with sensible defaults
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", 8000))
    # Enable CherryPy's built-in auto-reloader in development when requested
    debug = os.environ.get("DEV_RELOAD", "0") == "1"

    cherrypy.config.update(
        {
            "server.socket_host": host,
            "server.socket_port": port,
            "engine.autoreload.on": debug
        }
    )
    cherrypy.quickstart(app, '/', config)
