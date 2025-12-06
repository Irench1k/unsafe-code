from flask import Blueprint

from .e01_dual_auth_refund import bp as v301
from .e02_cart_swap_checkout import bp as v302
from .e03_menu_edits import bp as v303
from .e04_body_override_orders import bp as v304
from .e05_failed_update_leaks import bp as v305
from .e06_domain_token_any_mailbox import bp as v306
from .e07_token_swap_hijack import bp as v307
from .e08_fixed_final_version import bp as v308

bp = Blueprint("authorization_confusion", __name__)


@bp.route("/")
def index():
    return "Authorization Confusion vulnerability examples\n"


bp.register_blueprint(v301, url_prefix="v301")
bp.register_blueprint(v302, url_prefix="v302")
bp.register_blueprint(v303, url_prefix="v303")
bp.register_blueprint(v304, url_prefix="v304")
bp.register_blueprint(v305, url_prefix="v305")
bp.register_blueprint(v306, url_prefix="v306")
bp.register_blueprint(v307, url_prefix="v307")
bp.register_blueprint(v308, url_prefix="v308")
