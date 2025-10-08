"""
Admin Blueprint - Administrative interface routes

KEY SECURITY OBSERVATION: Blueprint namespacing is NOT a security boundary.
It provides organization and naming isolation, but does NOT provide:
- Authentication/authorization (anyone can access /admin/ routes)
- Data isolation (routes can access any app data)
- Request validation (blueprint doesn't enforce input rules)

Compare to foundations/python/flask/routing-multifile-register/admin/routes.py
which needed explicit endpoint names ('admin.list_users') to avoid collisions.
Blueprints solve this automatically with namespace prefixing.
"""
from flask import Blueprint

# Blueprint 'admin' creates third namespace alongside 'users' and 'posts'
admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
def index():
    """
    Admin dashboard - same 'index' function name as users/posts blueprints.

    Endpoint: 'admin.index' (no conflict with users.index or posts.index)
    Full path: /admin/
    """
    return "Admin: Dashboard"


@admin_bp.route('/users')
def list_users():
    """
    Admin view of users - demonstrates distinct functionality from users.index.

    In real apps: might show additional admin-only fields, moderation controls.
    For security review: verify proper authorization before showing admin data.
    """
    return "Admin: List all users (with admin details)"


@admin_bp.route('/users/<int:user_id>')
def manage_user(user_id):
    """
    Admin user management - different from users.detail endpoint.

    Endpoint: 'admin.manage_user' (distinct from 'users.detail')
    Full path: /admin/users/<user_id>

    Security note: Route structure doesn't enforce authorization.
    Both /users/<id> and /admin/users/<id> are public unless protected.
    """
    return f"Admin: Manage user {user_id}"


@admin_bp.route('/posts')
def list_posts():
    """
    Admin view of posts - demonstrates parallel structure to users admin.

    Common pattern: Admin blueprint mirrors other blueprints with elevated views.
    Security consideration: Ensure admin checks happen in code, not just routing.
    """
    return "Admin: List all posts (with moderation controls)"
