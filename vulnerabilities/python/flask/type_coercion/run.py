import os

from webapp import create_app

app = create_app()

if __name__ == "__main__":
    # Get configuration from environment variables with sensible defaults
    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", 8000))

    app.run(host=host, port=port)
