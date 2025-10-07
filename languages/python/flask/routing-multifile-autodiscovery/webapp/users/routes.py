# Blueprint approach for auto-discovery
#
# Export 'bp' Blueprint - gets automatically registered by auto-discovery

from flask import Blueprint

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/')
def list_users():
    return {"users": ["alice", "bob", "charlie"]}

@bp.route('/<int:user_id>')
def get_user(user_id):
    return {"user_id": user_id, "name": f"user_{user_id}"}
