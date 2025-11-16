from flask import Blueprint

# Create the main blueprint
bp = Blueprint("e01_dual_auth_refund_approval", __name__)

# Import middleware to ensure decorators execute
from .auth import middleware  # noqa: E402, F401

# Import all sub-blueprints from routes package
from .routes import account, auth, cart, menu, orders  # noqa: E402


@bp.route("/")
def index():
    return "R03: Authorization Confusion - Dual Auth Refund Approval\n"


# Register all routes with the main blueprint
bp.register_blueprint(account.bp)
bp.register_blueprint(menu.bp)
bp.register_blueprint(cart.bp)
bp.register_blueprint(orders.bp)
bp.register_blueprint(auth.bp)

__all__ = ["bp"]
