import logging

from flask import Blueprint, g, jsonify, request

# Initialize database when the blueprint is registered
from .config import load_config
from .database.db import close_session, get_session, init_database

# Create the main blueprint
bp = Blueprint("e01_dual_auth_refund_approval", __name__)

logger = logging.getLogger(__name__)


_config = load_config()
_db_initialized = False


def _init_db_once():
    """Initialize the database once when the blueprint is first used."""
    global _db_initialized
    if not _db_initialized:
        logger.info("Initializing database for v301...")
        init_database(_config, drop_existing=_config.reinitialize_on_startup)
        _db_initialized = True
        logger.info("Database initialized successfully")


@bp.before_request
def setup_database_session():
    """Set up a database session for each request."""
    # Initialize DB on first request
    try:
        if request.endpoint and request.endpoint.endswith("platform_reset"):
            return
        _init_db_once()

        # Create a new session for this request
        g.db_session = get_session(_config)
    except Exception as exc:  # pragma: no cover - test helper guardrail
        logger.exception("Database setup failed")
        return jsonify({"error": str(exc)}), 500


@bp.teardown_request
def teardown_database_session(exception=None):
    """Clean up the database session after each request."""
    session = g.pop("db_session", None)
    if session is not None:
        if exception:
            session.rollback()
        close_session(session)


# Import middleware to ensure decorators execute
from .auth import middleware  # noqa: E402, F401

# Import all sub-blueprints from routes package
from .routes import account, auth, cart, menu, orders, platform, restaurants  # noqa: E402


@bp.route("/")
def index():
    return "R03: Authorization Confusion - Dual Auth Refund Approval\n"


# Register all routes with the main blueprint
bp.register_blueprint(account.bp)
bp.register_blueprint(menu.bp)
bp.register_blueprint(cart.bp)
bp.register_blueprint(orders.bp)
bp.register_blueprint(auth.bp)
bp.register_blueprint(restaurants.bp)
bp.register_blueprint(platform.bp)

__all__ = ["bp"]
