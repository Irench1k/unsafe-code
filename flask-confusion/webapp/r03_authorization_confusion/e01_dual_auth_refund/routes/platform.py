from decimal import Decimal

from flask import Blueprint, jsonify, request

from ..config import load_config
from ..database.db import init_database
from ..database.repository import find_user_by_email, increment_user_balance
from ..e2e_helpers import require_e2e_auth

bp = Blueprint("e01_platform", __name__)


@bp.route("/e2e/reset", methods=["POST"])
@require_e2e_auth
def e2e_reset():
    """E2E test helper: reset database to initial state."""
    try:
        config = load_config()
        init_database(config, drop_existing=True)
        return jsonify({"status": "reset"}), 200
    except Exception as exc:  # pragma: no cover - test helper guardrail
        return jsonify({"error": str(exc)}), 500


@bp.route("/e2e/balance", methods=["POST"])
@require_e2e_auth
def e2e_balance():
    """E2E test helper: set user balance to a specific amount."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id")
    amount = payload.get("balance")
    if not user_id or amount is None:
        return jsonify({"error": "user_id and balance required"}), 400
    if not find_user_by_email(user_id):
        return jsonify({"error": "user not found"}), 404
    inc = Decimal(str(amount)) - find_user_by_email(user_id).balance
    increment_user_balance(user_id, inc)
    return jsonify({"status": "ok", "user_id": user_id, "balance": str(amount)}), 200
