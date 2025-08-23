from flask import Flask
from .blueprint import bp


def create_app():
    # Create flask app
    application = Flask(__name__)

    # Mount routes from subdirectories via flask blueprints
    application.register_blueprint(bp)

    # Make the app listen

    # Return the app, to be used with:
    #   $ flask --app app run
    return application
