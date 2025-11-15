from flask import Blueprint

bp = Blueprint("e08_fixed_final_version", __name__)

# Import routes and middleware to ensure decorators execute
# This ensures all @bp.route and @bp.before_request decorators are registered
from . import routes  # noqa: E402, F401
from .auth import middleware  # noqa: E402, F401

__all__ = ["bp"]
