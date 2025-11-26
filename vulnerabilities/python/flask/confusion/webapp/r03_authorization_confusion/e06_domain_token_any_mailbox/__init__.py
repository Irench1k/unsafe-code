from flask import Blueprint

from .config import load_config, scenario
from .database.lifecycle import register_database_hooks

bp = Blueprint(scenario.slug, __name__)

# Load per-scenario configuration once and attach lifecycle hooks that
# initialize the database and manage request-scoped sessions.
_config = load_config()
register_database_hooks(bp, _config)

# Import middleware after the blueprint exists so decorators can attach.
from .auth import middleware  # noqa: E402, F401

# Import route modules so each blueprint can be registered below.
from .routes import (  # noqa: E402
    account,
    auth,
    cart,
    menu,
    orders,  # noqa: E402
    platform,
    restaurants,
)


@bp.route("/")
def index():
    return f"{scenario.version}: {scenario.category} - {scenario.name}\n"


for module in (account, menu, cart, orders, auth, restaurants, platform):
    bp.register_blueprint(module.bp)


__all__ = ["bp"]
