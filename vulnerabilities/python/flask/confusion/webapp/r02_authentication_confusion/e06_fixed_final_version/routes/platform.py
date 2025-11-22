from decimal import Decimal

from flask import Blueprint, jsonify, request

from ..database.repository import get_platform_api_key
from ..database.services import reset_for_tests, set_balance_for_tests

bp = Blueprint("e06_platform", __name__)


def _authorized():
    return request.headers.get("X-Admin-API-Key") == get_platform_api_key()


@bp.route("/platform/reset", methods=["POST"])
def platform_reset():
    if not _authorized():
        return jsonify({"error": "Forbidden"}), 403
    reset_for_tests()
    return jsonify({"status": "reset"}), 200


@bp.route("/platform/balance", methods=["POST"])
def platform_balance():
    if not _authorized():
        return jsonify({"error": "Forbidden"}), 403
    payload = request.get_json(silent=True) or {}
    user_id = payload.get("user_id") or "sandy@bikinibottom.sea"
    amount = payload.get("balance")
    if amount is None:
        return jsonify({"error": "balance required"}), 400
    if not set_balance_for_tests(user_id, Decimal(str(amount))):
        return jsonify({"error": "user not found"}), 404
    return jsonify({"status": "ok", "user_id": user_id, "balance": str(amount)}), 200
