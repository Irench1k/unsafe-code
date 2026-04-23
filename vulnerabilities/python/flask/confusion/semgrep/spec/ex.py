from flask import Blueprint, request

from .ex2 import get_item

bp = Blueprint("e01_dual_params", __name__)


@bp.route("/test-10", methods=["POST"])
def ex10():
    # ok: function-call-get
    item = get_item(request.form)
    print(item)
