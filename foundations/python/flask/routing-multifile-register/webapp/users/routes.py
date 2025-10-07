# Example 1: Function-based route registration
#
# Pros:
# - Route handlers are regular functions (easier to test)
# - Explicit route registration using app.add_url_rule()
# - Clear separation between handler logic and route mapping
# - Functions can be imported and used elsewhere if needed
#
# Cons: 
# - More verbose than decorators
# - Route path repeated in registration call

def register(app):
    """Register user-related routes using function-based approach."""
    app.add_url_rule('/users/', view_func=list_users, methods=['GET'])
    app.add_url_rule('/users/<int:user_id>', view_func=get_user, methods=['GET'])

def list_users():
    return "List of users"

def get_user(user_id):
    return f"User {user_id}"
