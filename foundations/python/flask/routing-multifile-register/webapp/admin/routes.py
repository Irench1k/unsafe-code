# Example 3: Function-based routes with consistent prefixes
#
# This builds on the users/ approach (users/routes.py) but adds a consistent prefix automatically.

def register(app, prefix='/admin'):
    """Register admin routes with consistent prefix."""

    # Note that we need to provide the explicit endpoint names ('admin.list_users', 'admin.get_user')
    # because without them, Flask will use the function names ('list_users', 'get_user') which will
    # cause a collision with the ones registered in the users/routes.py file!
    app.add_url_rule(f'{prefix}/', 'admin.list_users', view_func=list_users)
    app.add_url_rule(f'{prefix}/<int:user_id>', 'admin.get_user', view_func=get_user)

def list_users():
    """Admin view: List all users with additional admin info."""
    return "Admin: List all users (with admin details)"

def get_user(user_id):
    """Admin view: List all posts with moderation controls."""
    return f"Admin: Get user {user_id}"
