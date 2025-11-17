"""
Restaurant routes - endpoints for managing and viewing restaurants.
"""

from flask import Blueprint, jsonify

from ..database.repository import find_all_restaurants

bp = Blueprint("restaurants", __name__, url_prefix="/restaurants")


@bp.get("")
def list_restaurants():
    """Lists all restaurants in the system."""
    restaurants = find_all_restaurants()
    return jsonify(
        [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
            }
            for r in restaurants
        ]
    )
