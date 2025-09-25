import os
import time
import logging

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

log = logging.getLogger(__name__)

# This example's schema name (unique per example)
SCHEMA = "R05"

# Read connection params from env (docker compose sets these)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://unsafe:code@db:5432/lab")

def redacted_dsn() -> str:
    """Render the DSN with password hidden for safe logging."""
    try:
        return make_url(DATABASE_URL).render_as_string(hide_password=True)
    except Exception:
        # Fallback: crude redaction if parsing fails
        return DATABASE_URL.replace("@", ":***@")

# Base engine (no search_path). Only used to create the schema.
_admin_engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)

_schema_engine: Engine | None = None

def ensure_schema() -> None:
    """Create this example's schema once. Safe to call multiple times."""
    log.info('Ensuring schema exists: "%s" (DSN=%s)', SCHEMA, redacted_dsn())
    with _admin_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))

def make_engine_for_schema() -> Engine:
    """
    Return an engine whose connections have search_path pinned to this example's schema.
    Keeps models schema-agnostic.
    """
    global _schema_engine
    if _schema_engine is None:
        log.info(
            'Creating schema engine (search_path=%s,public) (DSN=%s)',
            SCHEMA, redacted_dsn()
        )
        _schema_engine = create_engine(
            DATABASE_URL,
            future=True,
            pool_pre_ping=True,
            connect_args={"options": f"-csearch_path={SCHEMA},public"},
        )
    return _schema_engine

def wait_for_db(engine=None, tries: int = 30, delay: float = 1.0) -> None:
    """
    Ping the DB with SELECT 1; retry on OperationalError / network errors.
    Useful at startup to fail fast with good logs.
    """
    eng = engine or _admin_engine
    for i in range(1, tries + 1):
        try:
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            log.info("DB ping successful on try %d/%d (DSN=%s)", i, tries, redacted_dsn())
            return
        except OperationalError as e:
            log.warning("DB ping failed (%s) try %d/%d; retrying in %.1fs", e, i, tries, delay)
            time.sleep(delay)
        except OSError as e:
            log.warning("DB ping OS error (%s) try %d/%d; retrying in %.1fs", e, i, tries, delay)
            time.sleep(delay)
    raise RuntimeError(f"DB not reachable after {tries} tries (DSN={redacted_dsn()})")

# Session factory bound to the cached schema engine
_SessionLocal = None  # late init

def _session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        engine = make_engine_for_schema()
        _SessionLocal = sessionmaker(
            bind=engine,
            autoflush=True
        )
    return _SessionLocal

def make_session():
    """Fresh session bound to the cached schema engine."""
    return _session_factory()()
