"""
Database Engine and Session Management

This module handles SQLAlchemy engine creation, session management,
and database initialization for the v301 scenario.
"""

import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from ..config import Config
from .fixtures import (
    get_cart_items,
    get_carts,
    get_menu_items,
    get_order_items,
    get_orders,
    get_platform_config,
    get_refunds,
    get_restaurants,
    get_users,
)
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


def init_database(config: Config, drop_existing: bool = True):
    """
    Initialize the database schema and load fixtures.

    Args:
        config: Configuration object
        drop_existing: If True, drop existing schema before creating
    """
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
    """Load bootstrap data into the database."""
    session_factory = get_session_factory(config)
    session = session_factory()

    try:
        # Load all fixtures in order (respecting dependencies)
        logger.debug("Loading restaurants")
        restaurants = get_restaurants()
        session.add_all(restaurants)
        session.flush()

        logger.debug("Loading users")
        users = get_users()
        session.add_all(users)
        session.flush()

        logger.debug("Loading menu items")
        krusty = next(r for r in restaurants if r.name == "Krusty Krab")
        menu_items = get_menu_items(restaurant_id=krusty.id)
        session.add_all(menu_items)
        session.flush()

        logger.debug("Loading orders")
        spongebob = next(u for u in users if u.email == "spongebob@bikinibottom.sea")
        orders = get_orders(restaurant_id=krusty.id, user_id=spongebob.id)
        session.add_all(orders)
        session.flush()

        logger.debug("Loading order items")
        menu_item_by_name = {item.name: item for item in menu_items}
        order_items = get_order_items(
            order_id=orders[0].id,
            items=[
                menu_item_by_name["Krusty Krab Complect"],
                menu_item_by_name["Krabby Patty"],
            ],
        )
        session.add_all(order_items)
        session.flush()

        logger.debug("Loading carts")
        carts = get_carts(restaurant_id=krusty.id)
        session.add_all(carts)
        session.flush()

        logger.debug("Loading cart items")
        cart_items = get_cart_items(
            cart_id=carts[0].id,
            items=[
                menu_item_by_name["Krabby Patty"],
                menu_item_by_name["Side of Fries"],
            ],
        )
        session.add_all(cart_items)
        session.flush()

        logger.debug("Loading refunds")
        refunds = get_refunds(order_id=orders[0].id)
        session.add_all(refunds)
        session.flush()

        logger.debug("Loading platform config")
        config_items = get_platform_config()
        session.add_all(config_items)

        session.commit()
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
