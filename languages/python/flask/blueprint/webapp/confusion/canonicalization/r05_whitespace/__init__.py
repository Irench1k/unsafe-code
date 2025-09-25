import logging
import os

from flask import Blueprint

from .db import SCHEMA, ensure_schema, make_engine_for_schema, make_session, wait_for_db, redacted_dsn
from .models import Base
from .routes import bp
from .seed import seed_database

log = logging.getLogger(__name__)

@bp.before_request
def create_session():
    """Create database session per request."""
    from flask import g
    g.db_session = make_session()

@bp.teardown_request
def close_db(error):
    """Clean up database session at the end of each request."""
    from flask import g
    s = getattr(g, 'db_session', None)
    if not s:
        return
    try:
        if error:
            log.error("Rolling back database session due to error: %s", error)
            s.rollback()
    finally:
        s.close()

def _in_reloader_parent() -> bool:
    # In debug, parent has WERKZEUG_RUN_MAIN unset; child has it == "true"
    return os.getenv("WERKZEUG_RUN_MAIN") != "true"

def register(app: Blueprint) -> None:
    """
    Register blueprint and (optionally) auto-init schema/tables/seed for this example.
    This file depends only on this example's own modules.
    """
    app.register_blueprint(bp)

    log.info("Registering example blueprint, DSN=%s, schema=%s", redacted_dsn(), SCHEMA)

    # Skip seeding in the reloader parent
    if _in_reloader_parent():
        log.info("Debug reloader parent detected; skipping init/seed in this process.")
        return

    # 1) Verify the DB is reachable early, with clear logs
    wait_for_db()  # pings using admin engine (no search_path)

    # 2) Ensure schema
    ensure_schema()

    # 3) Ping the schema-engine explicitly (search_path applied)
    engine = make_engine_for_schema()
    wait_for_db(engine)

    # 4) Create tables and seed demo data
    log.info("Creating tables in schema %s", SCHEMA)
    Base.metadata.create_all(engine)

    session = make_session()
    try:
        log.info("Seeding demo data into schema %s…", SCHEMA)
        seed_database(session)
        session.commit()
        log.info("Seeding complete.")
    except Exception:
        session.rollback()
        log.exception("Seeding failed; rolled back.")
        raise
    finally:
        session.close()
