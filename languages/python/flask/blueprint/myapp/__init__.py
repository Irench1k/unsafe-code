from flask import Flask
from .demo.blueprint import bp


def create_app():
    # Create flask app
    app = Flask(__name__)

    @app.route("/")
    def index():
        return "Index Page: go check out /demo and other pages \n"

    # Mount routes from subdirectories via flask blueprints
    app.register_blueprint(bp, url_prefix="/demo")

    # Make the app listen

    # Return the app, to be used with:
    #   $ flask --app app run
    return app
