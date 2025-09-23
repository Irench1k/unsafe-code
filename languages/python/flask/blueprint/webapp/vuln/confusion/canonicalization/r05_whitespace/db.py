from __future__ import annotations
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# This example's schema name (unique per example)
SCHEMA = "R05"

# Read connection params from env (docker compose sets these)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://unsafe:code@db:5432/lab")

# Base engine (no search_path). Only used to create the schema.
_admin_engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)

def ensure_schema() -> None:
    """Create this example's schema once. Safe to call multiple times."""
    with _admin_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))

def make_engine_for_schema():
    """
    Return an engine whose connections have search_path pinned to this example's schema.
    Keeps models schema-agnostic.
    """
    return create_engine(
        DATABASE_URL,
        future=True,
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={SCHEMA},public"},
    )

def make_session():
    """Fresh session bound to a schema-pinned engine."""
    engine = make_engine_for_schema()
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
