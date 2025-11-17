"""
Configuration for v302 scenario.

This module provides configuration specific to this example/blueprint.
Since all blueprints run in the same Flask process, we can't rely on
environment variables alone (they would be shared). Instead, we read
the DATABASE_URL from environment but use hardcoded values for
blueprint-specific settings like schema name.
"""

import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Config:
    # Database connection string (shared across all blueprints)
    database_url: str

    # Schema name for this specific scenario (isolated from other blueprints)
    schema_name: str = "v302"

    # Whether to reinitialize the database on startup
    # (drop existing schema and recreate with fixtures)
    reinitialize_on_startup: bool = True


def load_config() -> Config:
    """Load configuration from environment variables."""
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://unsafe:code@localhost:5432/lab"
    )

    # Strip quotes if present (Docker Compose may add them)
    if database_url:
        database_url = database_url.strip('"').strip("'")

    return Config(database_url=database_url)


class OrderConfig:
    DELIVERY_FEE = Decimal("5.00")
    FREE_DELIVERY_ABOVE = Decimal("25.00")
    DEFAULT_REFUND_PERCENTAGE = Decimal("0.2")
    SIGNUP_BONUS = Decimal("2.00")
