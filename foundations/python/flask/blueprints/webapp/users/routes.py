"""
Users Blueprint - User management routes

Blueprint pattern benefits:
- Route handlers can use simple names (index, detail) without global conflicts
- All user-related functionality is grouped in one module
- URL prefix (/users/) is set once during blueprint registration
"""
from flask import Blueprint

# Create blueprint: name used for url_for() and endpoint generation
# Blueprint name becomes the namespace: 'users.index', 'users.detail', etc.
users_bp = Blueprint('users', __name__)


@users_bp.route('/')
def index():
    """List all users - note the simple function name doesn't conflict."""
    return "Users: List all users"


@users_bp.route('/<int:user_id>')
def detail(user_id):
    """
    Get specific user details.

    Route parameters work the same as regular Flask routes.
    Endpoint: 'users.detail' (blueprint name + function name)
    """
    return f"Users: Get user {user_id}"


@users_bp.route('/<int:user_id>/profile')
def profile(user_id):
    """
    User profile view - demonstrates nested paths under blueprint prefix.
    Full path: /users/<user_id>/profile
    """
    return f"Users: Profile for user {user_id}"
