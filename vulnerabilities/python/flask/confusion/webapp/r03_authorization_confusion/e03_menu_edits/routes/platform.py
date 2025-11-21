from decimal import Decimal

from flask import Blueprint, jsonify, request

from ..config import load_config
from ..database.db import init_database
from ..database.repository import find_user_by_email, increment_user_balance

bp = Blueprint("e03_platform", __name__)

ADMIN_KEY = "key-sandy-42841a8d-0e65-41db-8cce-8588c23e53dc"


def _authorized():
    return request.headers.get("X-Admin-API-Key") == ADMIN_KEY


@bp.route("/platform/reset", methods=["POST"])
def platform_reset():
    if not _authorized():
        return jsonify({"error": "Forbidden"}), 403
    config = load_config()
    init_database(config, drop_existing=True)
    return jsonify({"status": "reset"}), 200


@bp.route("/platform/balance", methods=["POST"])
def platform_balance():
    if not _authorized():
        return jsonify({"error": "Forbidden"}), 403
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
