"""Manual parameter-policy coverage fixture for CONF-002.

Purpose:
- exercise CONF-002 against representative singular/plural parameter confusion
  shapes
- document where the current broad key-pair heuristic is noisy
- provide a baseline for comparing CONF-002-OLD with a future site-based
  CONF-002-NEW implementation

How to scan manually:
    confusion-scan sast/tests/fixtures_conf002_parameter_policy_coverage.py --rules CONF-002

Each scenario has three labels:
- Confusion = True/False: whether the code is a review-worthy parameter-name
  confusion candidate under the thesis definition.
- Expect Current Find = True/False: whether the current CONF-002 heuristic is
  expected to report it.
- Expect New Find = True/False: whether the proposed site-based CONF-002-NEW
  should report it.

Definition used here:
Parameter-name confusion requires at least two places that interpret the same
attacker-controlled logical input family differently. A single local
compatibility fallback such as ``item`` OR ``items`` is not enough on its own.
"""

from decimal import Decimal

from flask import Blueprint, jsonify, request

bp = Blueprint("conf002_parameter_policy_coverage", __name__)


# ============================================================================
# Shared Helpers
# ============================================================================


def item_exists(item_id):
    return item_id in {"krabby_patty", "kelp_fries", "safe_item"}


def items_are_available(item_ids):
    return all(item_exists(item_id) for item_id in item_ids)


def item_price(item_id):
    if not item_exists(item_id):
        return None
    return Decimal("3.50")


def price_items(item_ids):
    total = Decimal("0.00")
    for item_id in item_ids:
        price = item_price(item_id)
        if price is None:
            return None
        total += price
    return total


def place_order(item_ids):
    return {"ordered_items": list(item_ids)}


def validate_single_item(data):
    item = data.get("item")
    return item if item_exists(item) else None


def validate_many_items(data):
    items = data.getlist("items")
    return items if items_are_available(items) else None


def build_many_items(data):
    return data.getlist("items")


def calculate_price_item_then_items(data):
    if "item" in data:
        items = [data.get("item")]
    else:
        items = data.getlist("items")
    return price_items(items)


def build_order_items_items_then_item(data):
    item_ids = data.getlist("items") or [data.get("item")]
    return item_ids


def calculate_price_items_then_item(data):
    item_ids = data.getlist("items") or [data.get("item")]
    return price_items(item_ids)


def build_order_items_item_then_items(data):
    if "item" in data:
        return [data.get("item")]
    return data.getlist("items")


def validate_single_item_id(data):
    item_id = data.get("item_id")
    return item_id if item_exists(item_id) else None


def build_many_item_ids(data):
    return data.getlist("item_ids")


def read_item_family(data):
    return data.get("item") or data.getlist("items")


def read_items_family(data):
    return data.getlist("items") or [data.get("item")]


def read_named(data, name):
    return data.get(name)


def read_keyword_item(*, data):
    return data.get("item")


def read_keyword_items(*, data):
    return data.getlist("items")


def get_request_parameter(parameter):
    return request.form.get(parameter) or request.args.get(parameter)


# ============================================================================
# Confusion=True, current and new rules should find
# ============================================================================


@bp.post("/find/opposite-helper-precedence")
def find_opposite_helper_precedence():
    # Confusion=True; Expect Current Find=True; Expect New Find=True; family=item/items
    # Price check prefers singular item, but order creation prefers plural items.
    total_price = calculate_price_item_then_items(request.form)
    if not total_price:
        return jsonify({"error": "unavailable item"}), 400

    item_ids = build_order_items_items_then_item(request.form)
    return jsonify(place_order(item_ids))


@bp.post("/find/direct-validation-singular-execution-plural")
def find_direct_validation_singular_execution_plural():
    # Confusion=True; Expect Current Find=True; Expect New Find=True; family=item/items
    # One site validates singular item, another site executes plural items.
    checked_item = request.form.get("item")
    if not item_exists(checked_item):
        return jsonify({"error": "unknown item"}), 400

    ordered_items = request.form.getlist("items")
    return jsonify(place_order(ordered_items))


@bp.post("/find/split-helper-components")
def find_split_helper_components():
    # Confusion=True; Expect Current Find=True; Expect New Find=True; family=item/items
    # Validation and execution helpers interpret the item family differently.
    checked_item = validate_single_item(request.form)
    if not checked_item:
        return jsonify({"error": "unknown item"}), 400

    ordered_items = validate_many_items(request.form)
    return jsonify(place_order(ordered_items))


@bp.post("/find/item-id-vs-item-ids")
def find_item_id_vs_item_ids():
    # Confusion=True; Expect Current Find=True; Expect New Find=True; family=item_id/item_ids
    # The item_id check can pass while item_ids controls the order content.
    checked_item_id = validate_single_item_id(request.form)
    if not checked_item_id:
        return jsonify({"error": "unknown item"}), 400

    ordered_item_ids = build_many_item_ids(request.form)
    return jsonify(place_order(ordered_item_ids))


@bp.post("/find/direct-and-helper")
def find_direct_and_helper():
    # Confusion=True; Expect Current Find=True; Expect New Find=True; family=item/items
    # The route validates one name and a helper consumes the plural variant.
    checked_item = request.form.get("item")
    if not item_exists(checked_item):
        return jsonify({"error": "unknown item"}), 400

    ordered_items = build_many_items(request.form)
    return jsonify(place_order(ordered_items))


@bp.post("/find/different-sources-same-parameter-family")
def find_different_sources_same_parameter_family():
    # Confusion=True; Expect Current Find=True; Expect New Find=True; family=item/items
    # Source disagreement is extra context, but the parameter family also diverges.
    checked_item = request.args.get("item")
    if not item_exists(checked_item):
        return jsonify({"error": "unknown item"}), 400

    ordered_items = request.form.getlist("items")
    return jsonify(place_order(ordered_items))


@bp.post("/find/two-local-family-policies")
def find_two_local_family_policies():
    # Confusion=True; Expect Current Find=True; Expect New Find=True; family=item/items
    # Two local policies support both names, but disagree on precedence.
    checked_items = request.form.get("item") or request.form.getlist("items")
    if not checked_items:
        return jsonify({"error": "items required"}), 400

    ordered_items = request.form.getlist("items") or [request.form.get("item")]
    return jsonify(place_order(ordered_items))


# ============================================================================
# Confusion=False, current rule should skip and new rule should skip
# ============================================================================


@bp.post("/ignore/same-key-cardinality-only")
def ignore_same_key_cardinality_only():
    # Confusion=False; Expect Current Find=False; Expect New Find=False; key=items
    # This belongs to CONF-003, not parameter-name confusion.
    first_item = request.form.get("items")
    all_items = request.form.getlist("items")
    return jsonify({"first": first_item, "all": all_items})


@bp.post("/ignore/unrelated-parameter-names")
def ignore_unrelated_parameter_names():
    # Confusion=False; Expect Current Find=False; Expect New Find=False
    # Different business concepts are not a singular/plural family.
    coupon = request.form.get("coupon")
    delivery_address = request.form.get("delivery_address")
    return jsonify({"coupon": coupon, "delivery_address": delivery_address})


@bp.post("/ignore/plural-word-outside-simple-rule")
def ignore_plural_word_outside_simple_rule():
    # Confusion=False; Expect Current Find=False; Expect New Find=False
    # Avoid clever stemming: status/statuses should not be guessed initially.
    status = request.form.get("status")
    statuses = request.form.getlist("statuses")
    return jsonify({"status": status, "statuses": statuses})


@bp.post("/ignore/item-only")
def ignore_item_only():
    # Confusion=False; Expect Current Find=False; Expect New Find=False; key=item
    item = request.form.get("item")
    return jsonify({"item": item})


@bp.post("/ignore/items-only")
def ignore_items_only():
    # Confusion=False; Expect Current Find=False; Expect New Find=False; key=items
    items = request.form.getlist("items")
    return jsonify({"items": items})


# ============================================================================
# Confusion=False, current false positives that CONF-002-NEW should skip
# ============================================================================


@bp.post("/fp/single-local-compatibility-fallback")
def fp_single_local_compatibility_fallback():
    # Confusion=False; Expect Current Find=True; Expect New Find=False; family=item/items
    # One local compatibility policy accepts old and new clients.
    item_ids = request.form.getlist("items") or [request.form.get("item")]
    return jsonify(place_order(item_ids))


@bp.post("/fp/transparent-return-both-values")
def fp_transparent_return_both_values():
    # Confusion=False; Expect Current Find=True; Expect New Find=False; family=item/items
    # Both values are returned transparently; there is no check/use split.
    item = request.form.get("item")
    items = request.form.getlist("items")
    return jsonify({"item": item, "items": items})


@bp.post("/fp/defensive-consistency-check")
def fp_defensive_consistency_check():
    # Confusion=False; Expect Current Find=True; Expect New Find=False; family=item/items
    # Ambiguity is explicitly detected and rejected.
    item = request.form.get("item")
    items = request.form.getlist("items")
    if item and items and items != [item]:
        return jsonify({"error": "send item only once"}), 400
    return jsonify(place_order(items or [item]))


@bp.post("/fp/explicit-api-mode-split")
def fp_explicit_api_mode_split():
    # Confusion=False; Expect Current Find=True; Expect New Find=False; family=item/items
    # The mode intentionally selects a singular or bulk API shape.
    mode = request.form.get("mode")
    if mode == "single":
        item_ids = [request.form.get("item")]
    else:
        item_ids = request.form.getlist("items")
    return jsonify(place_order(item_ids))


@bp.route("/fp/method-based-split", methods=["GET", "POST"])
def fp_method_based_split():
    # Confusion=False; Expect Current Find=True; Expect New Find=False; family=item/items
    # GET and POST represent mutually exclusive request shapes.
    if request.method == "GET":
        item_id = request.args.get("item")
        return jsonify({"preview": item_id})

    item_ids = request.form.getlist("items")
    return jsonify(place_order(item_ids))


@bp.post("/fp/logging-only-secondary-variant")
def fp_logging_only_secondary_variant():
    # Confusion=False; Expect Current Find=True; Expect New Find=False; family=item/items
    # The singular value is telemetry only; plural items drive behavior.
    debug_item = request.form.get("item")
    ordered_items = request.form.getlist("items")
    print("debug single item:", debug_item)
    return jsonify(place_order(ordered_items))


@bp.post("/fp/same-helper-same-family-policy")
def fp_same_helper_same_family_policy():
    # Confusion=False; Expect Current Find=True; Expect New Find=False; family=item/items
    # The same compatibility helper is reused with one stable policy.
    first = read_items_family(request.form)
    second = read_items_family(request.form)
    return jsonify({"first": first, "second": second})


@bp.post("/fp/normalization-to-canonical-list")
def fp_normalization_to_canonical_list():
    # Confusion=False; Expect Current Find=True; Expect New Find=False; family=item/items
    # The endpoint normalizes both request shapes into one canonical variable.
    raw_items = request.form.getlist("items")
    if raw_items:
        item_ids = raw_items
    else:
        item_ids = [request.form.get("item")]
    return jsonify(place_order(item_ids))


# ============================================================================
# Confusion=True, current and proposed new rules are expected to miss
# ============================================================================


@bp.before_request
def middleware_single_item_check():
    # Confusion=True; Expect Current Find=False; Expect New Find=False; family=item/items
    # Real candidate: middleware validates singular item, handler consumes plural items.
    # Current limitation: endpoint access grouping is handler-reachable only.
    if request.path.endswith("/miss/middleware-vs-handler"):
        request.args.get("item")


@bp.post("/miss/middleware-vs-handler")
def miss_middleware_vs_handler():
    # Confusion=True; Expect Current Find=False; Expect New Find=False; family=item/items
    ordered_items = request.form.getlist("items")
    return jsonify(place_order(ordered_items))


@bp.post("/miss/dynamic-helper-key")
def miss_dynamic_helper_key():
    # Confusion=True; Expect Current Find=False; Expect New Find=False; family=item/items
    # Literal key does not flow through the helper parameter.
    checked_item = read_named(request.form, "item")
    if not item_exists(checked_item):
        return jsonify({"error": "unknown item"}), 400

    ordered_items = read_named(request.form, "items")
    return jsonify(place_order([ordered_items]))


@bp.post("/miss/request-parameter-helper")
def miss_request_parameter_helper():
    # Confusion=True; Expect Current Find=False; Expect New Find=False; family=item/items
    # Dynamic request-key helper hides the singular key from the fact model.
    checked_item = get_request_parameter("item")
    if not item_exists(checked_item):
        return jsonify({"error": "unknown item"}), 400

    ordered_items = request.form.getlist("items")
    return jsonify(place_order(ordered_items))


@bp.post("/miss/keyword-helper-argument")
def miss_keyword_helper_argument():
    # Confusion=True; Expect Current Find=False; Expect New Find=False; family=item/items
    # Keyword argument propagation is not resolved precisely by the current graph.
    checked_item = read_keyword_item(data=request.form)
    if not item_exists(checked_item):
        return jsonify({"error": "unknown item"}), 400

    ordered_items = read_keyword_items(data=request.form)
    return jsonify(place_order(ordered_items))


@bp.post("/miss/semantic-alias-not-singular-plural")
def miss_semantic_alias_not_singular_plural():
    # Confusion=True; Expect Current Find=False; Expect New Find=False; family=item/menu_item
    # Same logical concept, but not detectable by simple singular/plural naming.
    checked_item = request.form.get("item")
    if not item_exists(checked_item):
        return jsonify({"error": "unknown item"}), 400

    ordered_item = request.form.get("menu_item")
    return jsonify(place_order([ordered_item]))


@bp.post("/miss/container-alias-flow")
def miss_container_alias_flow():
    # Confusion=True; Expect Current Find=False; Expect New Find=False; family=item/items
    # Request containers are hidden inside a dict before access.
    sources = {"single": request.form, "many": request.form}
    checked_item = sources["single"].get("item")
    if not item_exists(checked_item):
        return jsonify({"error": "unknown item"}), 400

    ordered_items = sources["many"].getlist("items")
    return jsonify(place_order(ordered_items))
