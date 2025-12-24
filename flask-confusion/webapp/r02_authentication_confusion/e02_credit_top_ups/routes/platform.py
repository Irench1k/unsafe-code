from decimal import Decimal

from flask import Blueprint, jsonify, request

from ..database.services import reset_for_tests, set_balance_for_tests
from ..e2e_helpers import require_e2e_auth

bp = Blueprint("e02_platform", __name__)


@bp.route("/e2e/reset", methods=["POST"])
@require_e2e_auth
def e2e_reset():
    """E2E test helper: reset database to initial state."""
    reset_for_tests()
    return jsonify({"status": "reset"}), 200


@bp.route("/e2e/balance", methods=["POST"])
@require_e2e_auth
def e2e_balance():
    """E2E test helper: set user balance to a specific amount."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id") or "sandy@bikinibottom.sea"
    amount = payload.get("balance")
    if amount is None:
        return jsonify({"error": "balance required"}), 400
    if not set_balance_for_tests(user_id, Decimal(str(amount))):
        return jsonify({"error": "user not found"}), 404
    return jsonify({"status": "ok", "user_id": user_id, "balance": str(amount)}), 200
