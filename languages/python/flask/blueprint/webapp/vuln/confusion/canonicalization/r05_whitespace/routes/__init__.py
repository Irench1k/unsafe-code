from flask import Blueprint

from .groups import groups_bp
from .messages import messages_bp
from .organizations import organizations_bp
from .users import users_bp

bp = Blueprint("sqlalchemy", __name__, url_prefix="/example22")

# Register sub-blueprints with URL prefixes
bp.register_blueprint(organizations_bp, url_prefix="/organizations")
bp.register_blueprint(users_bp, url_prefix="/users")
bp.register_blueprint(groups_bp, url_prefix="/groups")
bp.register_blueprint(messages_bp, url_prefix="/messages")
