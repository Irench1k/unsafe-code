# Example 4: Decorator-based routes with consistent prefixes
#
# This builds on the posts/ approach (posts/routes.py) but adds a consistent prefix automatically.

def register(app, prefix='/api/v1'):
    """Register API routes with consistent prefix using decorators."""
    
    # Note that we need to provide the explicit endpoint names ('api.list_users', ...)
    # because without them, Flask will use the function names ('list_users', ...) which will
    # cause a collision with the ones registered in the posts/routes.py file!
    @app.route(f'{prefix}/users', endpoint='api.list_users')
    def list_users():
        return {"users": ["alice", "bob", "charlie"]}
    
    @app.route(f'{prefix}/users/<int:user_id>', endpoint='api.get_user')
    def get_user(user_id):
        return {"user_id": user_id, "name": f"User {user_id}"}
    
    @app.route(f'{prefix}/posts', endpoint='api.list_posts')
    def list_posts():
        return {"posts": ["post1", "post2", "post3"]}
    
    @app.route(f'{prefix}/posts/<int:post_id>', endpoint='api.get_post')
    def get_post(post_id):  
        return {"post_id": post_id, "title": f"Post {post_id}"}
