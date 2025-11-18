import logging

from flask import Blueprint, g

# Initialize database when the blueprint is registered
from .config import load_config
from .database.db import close_session, get_session, init_database

# Create the main blueprint
bp = Blueprint("e02_cart_swap_checkout", __name__)

logger = logging.getLogger(__name__)


_config = load_config()
_db_initialized = False


def _init_db_once():
    """Initialize the database once when the blueprint is first used."""
    global _db_initialized
    if not _db_initialized:
        logger.info("Initializing database...")
        init_database(_config, drop_existing=_config.reinitialize_on_startup)
        _db_initialized = True
        logger.info("Database initialized successfully")


@bp.before_request
def setup_database_session():
    """Create a scoped session *and* open an explicit transaction per request.

    Historically SQLAlchemy would autobegin a transaction on first query, which
    made it easy to forget there was already an open unit of work.

    We want the lifecycle to be loud and obvious: every request opens a session,
    immediately begins a transaction, and leaves responsibility for commit/rollback
    to teardown handlers. Handlers and decorators can rely on this predictable
    scope when they manipulate money or other sensitive records.
    """
    _init_db_once()

    g.db_session = get_session(_config)
    # Handlers should only use g.db_session. g._db_trasaction_handle is only
    # used by teardown_request to commit or rollback the transaction.
    g._db_transaction_handle = g.db_session.begin()


@bp.teardown_request
def teardown_database_session(exception=None):
    """Finalize the request-scoped transaction and close the session."""
    transaction = g.pop("_db_transaction_handle", None)
    session = g.pop("db_session", None)

    try:
        if transaction is not None:
            if exception:
                # Handler caused an exception, roll back the transaction to undo any changes.
                transaction.rollback()
            else:
                # Handler completed successfully, commit the transaction atomically.
                transaction.commit()
    except Exception:
        # Any failure during commit still needs an explicit rollback to avoid
        # poisoning the connection in the pool.
        if session is not None:
            session.rollback()
        logger.exception("Database transaction cleanup failed")
        raise
    finally:
        if session is not None:
            close_session(session)


# Import middleware to ensure decorators execute
from .auth import middleware  # noqa: E402, F401

# Import all sub-blueprints from routes package
from .routes import account, auth, cart, menu, orders, restaurants  # noqa: E402


@bp.route("/")
def index():
    return "R03: Authorization Confusion - Cart Swap Checkout\n"


# Register all routes with the main blueprint
bp.register_blueprint(account.bp)
bp.register_blueprint(menu.bp)
bp.register_blueprint(cart.bp)
bp.register_blueprint(orders.bp)
bp.register_blueprint(auth.bp)
bp.register_blueprint(restaurants.bp)

__all__ = ["bp"]
