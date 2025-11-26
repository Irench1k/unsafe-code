"""
E2E Testing Infrastructure

This module provides helpers for e2e test endpoints that are only active when
E2E_TESTING=true. These endpoints allow tests to reset database state and set
user balances for deterministic test runs.

In-universe explanation: These are "testing mode" endpoints that Sandy added
to help with automated testing. They're disabled in production via environment
checks.
"""

import os
from functools import wraps

from flask import jsonify, request


def is_e2e_enabled():
    """Check if E2E testing mode is enabled via environment variable."""
    return os.environ.get("E2E_TESTING", "").lower() == "true"


def require_e2e_auth(f):
    """
    Decorator to protect e2e endpoints.

    Checks two conditions:
    1. E2E_TESTING environment variable is set to "true"
    2. X-E2E-API-Key header matches E2E_API_KEY environment variable

    If E2E_TESTING is false, returns 404 (endpoint doesn't exist in production).
    If authentication fails, returns 403 (forbidden).
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        # E2E endpoints only exist in testing mode
        if not is_e2e_enabled():
            return jsonify({"error": "Not found"}), 404

        # Verify E2E API key
        expected_key = os.environ.get("E2E_API_KEY", "")
        provided_key = request.headers.get("X-E2E-API-Key", "")

        if not expected_key or provided_key != expected_key:
            return jsonify({"error": "Forbidden"}), 403

        return f(*args, **kwargs)

    return decorated
