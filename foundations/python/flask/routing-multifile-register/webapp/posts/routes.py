# Example 2: Decorator-based route registration
#
# Pros:
# - More Flask-idiomatic (uses @app.route decorators)
# - Less verbose, route definition stays close to handler
# - Familiar to most Flask developers
#
# Cons:
# - Route decorators are applied at registration time (not definition time)
# - Slightly harder to test handlers in isolation
# - Functions are nested inside register(), less reusable

def register(app):
    """Register post-related routes using decorator-based approach."""

    @app.route('/posts/', methods=['GET'])
    def list_posts():
        return "List of posts"

    @app.route('/posts/<int:post_id>', methods=['GET'])
    def get_post(post_id):
        return f"Post {post_id}"
