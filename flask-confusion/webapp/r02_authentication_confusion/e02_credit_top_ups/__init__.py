from flask import Blueprint

# Create the main blueprint
bp = Blueprint("e02_credit_top_ups", __name__)

# Import middleware to ensure decorators execute
from .auth import middleware  # noqa: E402, F401

# Import all sub-blueprints from routes package
from .routes import (  # noqa: E402
    account,
    auth,
    cart,
    index,
    menu,
    orders,
    platform,
)

# Register all sub-blueprints with the main blueprint
bp.register_blueprint(index.bp)
bp.register_blueprint(account.bp)
bp.register_blueprint(menu.bp)
bp.register_blueprint(cart.bp)
bp.register_blueprint(orders.bp)
bp.register_blueprint(auth.bp)
bp.register_blueprint(platform.bp)

__all__ = ["bp"]
