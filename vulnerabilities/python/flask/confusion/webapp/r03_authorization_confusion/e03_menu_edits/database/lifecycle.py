import logging

from flask import Blueprint, g

from ..config import Config
from .db import close_session, get_session, init_database

logger = logging.getLogger(__name__)


def register_database_hooks(bp: Blueprint, config: Config) -> None:
    """Attach request hooks that manage DB initialization and sessions."""

    db_initialized = False

    def _init_db_once() -> None:
        nonlocal db_initialized
        if db_initialized:
            return

        logger.info("Initializing database for %s", getattr(config, "schema_name", "unknown"))
        init_database(config, drop_existing=config.reinitialize_on_startup)
        db_initialized = True
        logger.info("Database initialized successfully")

    @bp.before_request
    def setup_database_session() -> None:
        """Create a scoped session and start an explicit transaction per request."""

        _init_db_once()

        g.db_session = get_session(config)
        # Handlers should only use g.db_session. g._db_transaction_handle is only used
        # by teardown_request to commit or rollback the transaction.
        g._db_transaction_handle = g.db_session.begin()

    @bp.teardown_request
    def teardown_database_session(exception: BaseException | None = None) -> None:
        """Finalize the request-scoped transaction and close the session."""

        transaction = g.pop("_db_transaction_handle", None)
        session = g.pop("db_session", None)

        try:
            if transaction is not None:
                if exception:
                    transaction.rollback()
                else:
                    transaction.commit()
        except Exception:
            if session is not None:
                session.rollback()
            logger.exception("Database transaction cleanup failed")
            raise
        finally:
            if session is not None:
                close_session(session)


__all__ = ["register_database_hooks"]
