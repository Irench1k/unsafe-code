from flask import Blueprint

from .e0103_intro.routes import bp as intro_bp
from .e04_cross_module.routes import bp as cross_module_bp
from .e0506_variations.routes import bp as variations_bp
from .e0708_apparent_fix.routes import bp as apparent_fix_bp

bp = Blueprint("source_precedence", __name__)

# Shared database - imported by subdirectories via "from .. import db"
db = {
    "passwords": {
        "spongebob": "bikinibottom",
        "squidward": "clarinet123",
        "mr.krabs": "money",
    },
    "messages": {
        "spongebob": [
            {"from": "patrick", "message": "SpongeBob! I'm ready! I'm ready! Let's go jellyfishing!"},
        ],
        "squidward": [
            {
                "from": "mr.krabs",
                "message": "Squidward, I'm switching yer shifts to Tuesday through Saturday. No complaints!",
            },
            {
                "from": "squidward",
                "message": "Note to self: Mr. Krabs hides the safe key under the register. Combination is his first dime's serial number.",
            },
        ],
        "mr.krabs": [
            {
                "from": "squidward",
                "message": "I saw Plankton buying a mechanical keyboard, he's planning to hack us!",
            },
        ],
    },
}


@bp.route("/")
def index():
    return "Source Precedence vulnerability examples\n"


# Register sub-blueprints without url_prefix to preserve URLs
bp.register_blueprint(intro_bp)
bp.register_blueprint(cross_module_bp)
bp.register_blueprint(variations_bp)
bp.register_blueprint(apparent_fix_bp)
