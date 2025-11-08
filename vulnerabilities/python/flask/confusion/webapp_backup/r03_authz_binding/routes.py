"""
Authorization Binding Drift Examples

This module demonstrates various forms of authorization binding drift, where
authentication successfully establishes WHO the user is, but user-controlled
parameters allow rebinding WHICH resource to act on or WHOSE identity to act as.
"""

from flask import Blueprint

# Import sub-blueprints for each example category
from .e01_baseline.routes import bp as baseline_bp
from .e02_path_query_confusion.routes import bp as path_query_confusion_bp
from .e03_simple_rebinding.routes import bp as simple_rebinding_bp

# Create main blueprint for authorization binding examples
bp = Blueprint("authz_binding", __name__)

# Register sub-blueprints
bp.register_blueprint(baseline_bp)
bp.register_blueprint(path_query_confusion_bp)
bp.register_blueprint(simple_rebinding_bp)
