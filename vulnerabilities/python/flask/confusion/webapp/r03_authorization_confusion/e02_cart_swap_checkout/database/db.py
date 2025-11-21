"""
Database Engine and Session Management

This module handles SQLAlchemy engine creation, session management,
and database initialization.
"""

import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from ..config import Config
from .fixtures import initialize_all_fixtures
from .models import Base

logger = logging.getLogger(__name__)

# Global variables for engine and session factory
_engine = None
_session_factory = None


def init_engine(config: Config):
    """
    Initialize the SQLAlchemy engine with proper schema configuration.

    This sets up the database connection with schema search path to ensure
    all operations are isolated to this scenario's schema.
    """
    global _engine

    if _engine is not None:
        logger.warning("Engine already initialized, skipping")
        return _engine

    # Create engine
    _engine = create_engine(
        config.database_url,
        echo=False,  # Set to True for SQL query logging
        pool_pre_ping=True,  # Verify connections before using
    )

    # Set up event listener to set search_path for each connection
    @event.listens_for(_engine, "connect")
    def set_search_path(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET search_path TO {config.schema_name}, public")
        cursor.close()

    logger.info(f"Database engine initialized for schema: {config.schema_name}")
    return _engine


def get_session_factory(config: Config):
    """Get or create the session factory."""
    global _session_factory

    if _session_factory is None:
        engine = get_engine(config)
        _session_factory = scoped_session(
            sessionmaker(bind=engine, autocommit=False, autoflush=False)
        )
        logger.debug("Session factory created")

    return _session_factory


def get_engine(config: Config):
    """Get the SQLAlchemy engine, initializing if necessary."""
    if _engine is None:
        init_engine(config)
    return _engine


def dispose_engine():
    """Dispose engine and session factory to clear prepared statements between resets."""
    global _engine, _session_factory
    if _session_factory is not None:
        _session_factory.remove()
        _session_factory = None
    if _engine is not None:
        _engine.dispose()
        _engine = None


def init_database(config: Config, drop_existing: bool = True):
    """
    Initialize the database schema and load fixtures.

    Args:
        config: Configuration object
        drop_existing: If True, drop existing schema before creating
    """
    if drop_existing:
        dispose_engine()

    engine = get_engine(config)

    # Create schema if it doesn't exist, or drop and recreate if requested
    with engine.connect() as conn:
        if drop_existing:
            logger.info(f"Dropping schema {config.schema_name} if exists")
            conn.execute(text(f"DROP SCHEMA IF EXISTS {config.schema_name} CASCADE"))
            conn.commit()

        logger.info(f"Creating schema {config.schema_name}")
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.schema_name}"))
        conn.commit()

        # Set search path for this connection
        conn.execute(text(f"SET search_path TO {config.schema_name}, public"))
        conn.commit()

    # Create all tables within the schema
    logger.info(f"Creating tables in schema {config.schema_name}")
    Base.metadata.create_all(engine)

    # Load fixtures
    logger.info("Loading fixtures")
    _load_fixtures(config)

    logger.info("Database initialization complete")


def _load_fixtures(config: Config):
    """
    Load bootstrap data into the database.

    This is now a simple wrapper around the comprehensive fixtures module.
    All fixture logic lives in fixtures.py for easy maintenance.
    """
    session_factory = get_session_factory(config)
    session = session_factory()

    try:
        # All fixture loading is handled by the fixtures module
        initialize_all_fixtures(session)
        logger.info("Fixtures loaded successfully")
    except Exception as e:
        logger.error(f"Error loading fixtures: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def get_session(config: Config) -> Session:
    """
    Get a new database session.

    This should be called once per request and the session should be closed
    when the request is complete.
    """
    session_factory = get_session_factory(config)
    return session_factory()


def close_session(session: Session):
    """Close a database session."""
    if session:
        session.close()
