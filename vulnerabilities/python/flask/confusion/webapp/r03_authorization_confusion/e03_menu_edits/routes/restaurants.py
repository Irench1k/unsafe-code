"""
Restaurant routes - endpoints for managing and viewing restaurants.
"""

from flask import Blueprint

from ..database.repository import find_all_restaurants
from ..utils import success_response

bp = Blueprint("restaurants", __name__, url_prefix="/restaurants")


@bp.get("")
def list_restaurants():
    """Lists all restaurants in the system."""
    restaurants = find_all_restaurants()
    return success_response(
        [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
            }
            for r in restaurants
        ]
    )
