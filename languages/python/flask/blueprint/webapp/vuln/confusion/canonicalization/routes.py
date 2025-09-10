from flask import Blueprint, request
from .r01_lowercase.routes import bp as lowercase_bp

# Confusion-based vulnerability examples
bp = Blueprint("canonicalization", __name__)
bp.register_blueprint(lowercase_bp)


@bp.route("/")
def index():
    return "Canonicalization confusion vulnerability examples\n"
