"""Shared test fixtures."""

from pathlib import Path

import pytest

# Root of the webapp with intentionally vulnerable exercises
WEBAPP_ROOT = Path(__file__).resolve().parent.parent.parent / "webapp"


@pytest.fixture
def webapp_root():
    return WEBAPP_ROOT


@pytest.fixture
def r01_root(webapp_root):
    return webapp_root / "r01_input_source_confusion"


@pytest.fixture
def r04_root(webapp_root):
    return webapp_root / "r04_cardinality_confusion"
