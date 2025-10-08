"""
Posts Blueprint - Content management routes

Demonstrates:
- Same function names (index, detail) as users blueprint without conflicts
- Multiple HTTP methods on single route
- Blueprint as organizational unit for related functionality
"""
from flask import Blueprint, request

# Blueprint name 'posts' creates separate namespace from 'users'
posts_bp = Blueprint('posts', __name__)


@posts_bp.route('/')
def index():
    """
    List all posts - same function name as users.index but no conflict.

    Endpoint: 'posts.index' (different from 'users.index')
    """
    return "Posts: List all posts"


@posts_bp.route('/<int:post_id>')
def detail(post_id):
    """
    Get specific post - same function name as users.detail but different endpoint.

    Endpoint: 'posts.detail'
    Full path: /posts/<post_id>
    """
    return f"Posts: Get post {post_id}"


@posts_bp.route('/create', methods=['GET', 'POST'])
def create():
    """
    Create new post - demonstrates handling multiple HTTP methods.

    Note: In real apps, this would handle form data or JSON.
    For security review: check how data flows from request to storage.
    """
    if request.method == 'POST':
        return "Posts: Create new post (POST)"
    return "Posts: Show create form (GET)"
