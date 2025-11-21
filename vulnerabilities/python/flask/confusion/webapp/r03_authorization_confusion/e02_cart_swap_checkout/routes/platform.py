from flask import Blueprint, jsonify, request

from ..config import load_config
from ..database.db import init_database

bp = Blueprint("e02_platform", __name__)

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
