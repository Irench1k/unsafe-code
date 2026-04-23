from flask import Blueprint, request

bp = Blueprint("e01_dual_params", __name__)


@bp.route("/test-1", methods=["POST"])
def ex1():
    # ruleid: function-call-get
    items = request.form.get("items")
    print(items)


@bp.route("/test-2", methods=["POST"])
def ex2():
    # ruleid: function-call-get
    item = request.form.get("item")
    print(item)


@bp.route("/test-3", methods=["POST"])
def ex3():
    # ok: function-call-get
    items = request.form.getlist("items")
    print(items)


@bp.route("/test-4", methods=["POST"])
def ex4():
    # ruleid: function-call-get
    item = [request.form.get("item")]
    print(item)


@bp.route("/test-5", methods=["POST"])
def ex5():
    # ruleid: function-call-get
    item = request.args.get("item")
    print(item)


@bp.route("/test-6", methods=["POST"])
def ex6():
    # ruleid: function-call-get
    item = request.values.get("item")
    print(item)


@bp.route("/test-7", methods=["POST"])
def ex7():
    # ruleid: function-call-get
    item = request.json.get("item")
    print(item)


@bp.route("/test-8", methods=["POST"])
def ex8():
    # ruleid: function-call-get
    item = request.get_json().get("item")
    print(item)


@bp.route("/test-9", methods=["POST"])
def ex9():
    data = {"item": 1}
    # ok: function-call-get
    item = data.get("item")
    print(item)


def get_item(data):
    # ruleid: function-call-get
    return data.get("qwe")


@bp.route("/test-10", methods=["POST"])
def ex10():
    # ok: function-call-get
    item = get_item(request.form)
    print(item)


@bp.route("/test-11", methods=["POST"])
def ex11():
    # ok: function-call-get
    item = get_item(request.args)
    print(item)


@bp.route("/test-12", methods=["POST"])
def ex12():
    # ok: function-call-get
    item = get_item(request.values)
    print(item)


@bp.route("/test-13", methods=["POST"])
def ex13():
    # ok: function-call-get
    item = get_item(request.json)
    print(item)


@bp.route("/test-14", methods=["POST"])
def ex14():
    # ok: function-call-get
    item = get_item(request.get_json())
    print(item)


@bp.route("/test-15", methods=["POST"])
def ex15():
    data = {"item": 1}
    # ok: function-call-get
    item = get_item(data)
    print(item)
