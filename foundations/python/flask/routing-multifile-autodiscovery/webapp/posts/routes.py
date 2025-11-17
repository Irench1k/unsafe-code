# Function registration approach for auto-discovery
#
# Export 'register(app)' function - gets automatically called by auto-discovery
# Shows both decorator and add_url_rule approaches

def register(app):
    """Register post routes using both decorator and function approaches."""

    # Approach 1: Using decorators inside register()
    @app.route('/posts/')
    def list_posts():
        return {"posts": ["post1", "post2", "post3"]}

    # Approach 2: Using add_url_rule() for explicit control
    app.add_url_rule('/posts/<int:post_id>', view_func=get_post)

def get_post(post_id):
    """Get post by ID - defined outside register() for reusability."""
    return {"post_id": post_id, "title": f"Post {post_id}"}
