from flask import Blueprint
from .r01_lowercase.routes import bp as lowercase_bp
from .r02_insensitive_object_retrieval.routes import bp as lowercase_2_bp
from .r03_whitespace.routes import bp as whitespace_bp
from .r04_whitespace.routes import bp as whitespace_bp_2
# Blueprints that have their own initialization logic
from .r05_whitespace import register as r05_whitespace_register

# Confusion-based vulnerability examples
bp = Blueprint("canonicalization", __name__)
bp.register_blueprint(lowercase_bp)
bp.register_blueprint(lowercase_2_bp)
bp.register_blueprint(whitespace_bp)
bp.register_blueprint(whitespace_bp_2)
r05_whitespace_register(bp)


@bp.route("/")
def index():
    return "Canonicalization confusion vulnerability examples\n"
