from flask import Blueprint

from .r01_lowercase.routes import bp as lowercase_bp
from .r02_insensitive_object_retrieval.routes import bp as lowercase_2_bp
from .r03_strip_replace_mismatch.routes import bp as strip_replace_mismatch_bp
from .r04_pydantic_strip_bypass.routes import bp as pydantic_strip_bypass_bp

# Normalization and Canonicalization vulnerability examples
bp = Blueprint("normalization_canonicalization", __name__)

# Register child blueprints
bp.register_blueprint(lowercase_bp)
bp.register_blueprint(lowercase_2_bp)
bp.register_blueprint(strip_replace_mismatch_bp)
bp.register_blueprint(pydantic_strip_bypass_bp)


@bp.route("/")
def index():
    return "Normalization and Canonicalization confusion vulnerability examples\n"
