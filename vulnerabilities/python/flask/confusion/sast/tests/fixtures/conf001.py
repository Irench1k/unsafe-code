"""Manual policy-coverage fixture for CONF-001.

Purpose:
- exercise CONF-001 against representative input-source confusion shapes
- keep enough false-positive probes to estimate precision before scanning OSS
- document known expected misses where the current graph/rule is too weak

How to scan manually:
    confusion-scan sast/tests/fixtures_conf001_policy_coverage.py --rules CONF-001

Each scenario has two independent labels:
- Confusion = True/False: whether the code is a review-worthy input-source
  confusion candidate under the thesis definition.
- Expect Find = True/False: whether current CONF-001 is expected to report it.

This gives the usual rule-evaluation matrix:
- Confusion=True, Expect Find=True: TP
- Confusion=True, Expect Find=False: FN
- Confusion=False, Expect Find=True: FP
- Confusion=False, Expect Find=False: TN

Definition used here:
Input Source Confusion requires at least two places that can interpret the same
attacker-controlled logical input differently in one request. A single local
fallback expression is not confusion.
"""

from decimal import Decimal

from flask import Blueprint, jsonify, request

bp = Blueprint("conf001_policy_coverage", __name__)


# ============================================================================
# Shared Helpers
# ============================================================================


def read_item(data):
    return data.get("item")


def read_coupon(data):
    return data.get("coupon")


def read_discount(data):
    return data.get("discount")


def validate_delivery_address(data):
    return data.get("delivery_address")


def calculate_delivery_address(data):
    return data.get("delivery_address")


def read_nested_outer(data):
    return read_nested_inner(data)


def read_nested_inner(data):
    return data.get("nested")


def read_keyword_data(*, data):
    return data.get("keyword")


def get_request_parameter(parameter):
    """Dynamic-key helper used to document current literal-key limits."""
    in_args = request.args.get(parameter)
    in_json = request.is_json and isinstance(request.json, dict) and request.json.get(parameter)
    in_form = request.form.get(parameter)
    return in_args or in_json or in_form


def item_exists(item_id):
    return item_id in {"krabby_patty", "kelp_fries", "safe_item"}


def place_order(item_id):
    return {"ordered_item": item_id}


def apply_discount(discount_code):
    return {"discount": discount_code}


def calculate_delivery_fee(sort_mode):
    return {"sort_mode": sort_mode}


def update_delivery_address(address):
    return {"delivery_address": address}


def load_account(account_id):
    return {"account_id": account_id}


def apply_theme(theme):
    return {"theme": theme}


def load_profile(profile_id):
    return {"profile_id": profile_id}


def apply_token(token):
    return {"token": token}


def upload_receipt(receipt):
    return {"receipt": str(receipt)}


# ============================================================================
# Confusion=True, Expect Find=True: true positives CONF-001 should catch
# ============================================================================


@bp.post("/find/direct-args-vs-form")
def find_direct_args_vs_form():
    # Confusion=True; Expect Find=True; key=item
    # Query item is validated, but form item is used to create the order.
    checked_item = request.args.get("item")
    if not item_exists(checked_item):
        return jsonify({"error": "unknown item"}), 400

    ordered_item = request.form.get("item")
    return jsonify(place_order(ordered_item))


@bp.post("/find/values-vs-args")
def find_values_vs_args():
    # Confusion=True; Expect Find=True; key=sort
    # Query sort is checked, but request.values can pick a conflicting form value.
    validated_sort = request.args.get("sort")
    if validated_sort not in {"distance", "price"}:
        return jsonify({"error": "unsupported sort"}), 400

    effective_sort = request.values.get("sort")
    return jsonify(calculate_delivery_fee(effective_sort))


@bp.post("/find/helper-form-vs-values")
def find_helper_form_vs_values():
    # Confusion=True; Expect Find=True; key=item
    # Helper validates request.form item, then same helper reads effective item from values.
    validated_item = read_item(request.form)
    if not item_exists(validated_item):
        return jsonify({"error": "unknown item"}), 400

    effective_item = read_item(request.values)
    return jsonify(place_order(effective_item))


@bp.post("/find/split-helper-components")
def find_split_helper_components():
    # Confusion=True; Expect Find=True; key=delivery_address
    # Validation and update components disagree on source policy for the same address.
    validated = validate_delivery_address(request.form)
    if not validated:
        return jsonify({"error": "delivery address required"}), 400

    effective = calculate_delivery_address(request.values)
    return jsonify(update_delivery_address(effective))


@bp.post("/find/many-sites-one-rival")
def find_many_sites_one_rival():
    # Confusion=True; Expect Find=True; key=discount
    # Form discount is checked in multiple places, but query discount is applied.
    initial_discount = request.form.get("discount")
    confirmed_discount = read_discount(request.form)
    if initial_discount != confirmed_discount:
        return jsonify({"error": "discount changed"}), 400

    effective_discount = request.args.get("discount")
    return jsonify(apply_discount(effective_discount))


@bp.post("/find/two-fallback-policies")
def find_two_fallback_policies():
    # Confusion=True; Expect Find=True; key=tip
    # Two distinct local normalization policies disagree: JSON/FORM vs JSON/ARGS.
    validation_data = request.json if request.is_json else request.form
    validated_tip = Decimal(validation_data.get("tip", 0))
    if validated_tip < 0:
        return jsonify({"error": "tip cannot be negative"}), 400

    execution_data = request.json if request.is_json else request.args
    effective_tip = Decimal(execution_data.get("tip", 0))

    return jsonify({"charged_tip": str(effective_tip)})


@bp.post("/find/source-precedence-difference")
def find_source_precedence_difference():
    # Confusion=True; Expect Find=True; key=coupon
    # The coupon check and application use opposite args/form precedence.
    validated_coupon = request.args.get("coupon") or request.form.get("coupon")
    if validated_coupon == "blocked":
        return jsonify({"error": "coupon blocked"}), 400

    effective_coupon = request.form.get("coupon") or request.args.get("coupon")
    return jsonify(apply_discount(effective_coupon))


@bp.post("/find/single-vs-fallback-policy")
def find_single_vs_fallback_policy():
    # Confusion=True; Expect Find=True; key=token
    # Validation uses one explicit source, execution uses a JSON/ARGS fallback.
    validated_token = request.form.get("token")
    if validated_token != "allowed":
        return jsonify({"error": "invalid token"}), 403

    execution_data = request.json if request.is_json else request.args
    effective_token = execution_data.get("token")
    return jsonify(apply_token(effective_token))


@bp.post("/find/single-vs-precedence-policy")
def find_single_vs_precedence_policy():
    # Confusion=True; Expect Find=True; key=coupon
    # Validation uses form only, execution prefers query and falls back to form.
    validated_coupon = request.form.get("coupon")
    if validated_coupon == "blocked":
        return jsonify({"error": "coupon blocked"}), 400

    effective_coupon = request.args.get("coupon") or request.form.get("coupon")
    return jsonify(apply_discount(effective_coupon))


@bp.post("/find/fallback-vs-precedence-policy")
def find_fallback_vs_precedence_policy():
    # Confusion=True; Expect Find=True; key=token
    # Validation uses JSON/FORM fallback, execution uses ARGS->FORM precedence.
    validation_data = request.json if request.is_json else request.form
    validated_token = validation_data.get("token")
    if validated_token != "allowed":
        return jsonify({"error": "invalid token"}), 403

    effective_token = request.args.get("token") or request.form.get("token")
    return jsonify(apply_token(effective_token))


@bp.post("/find/direct-json-vs-form")
def find_direct_json_vs_form():
    # Confusion=True; Expect Find=True; key=profile_id
    # Direct request.json.get is paired with request.form.get without a ternary alias.
    checked_profile = (
        request.json.get("profile_id")
        if request.is_json and isinstance(request.json, dict)
        else None
    )
    if checked_profile != "allowed":
        return jsonify({"error": "profile denied"}), 403

    effective_profile = request.form.get("profile_id")
    return jsonify(load_profile(effective_profile))


@bp.post("/find/subscript-vs-get")
def find_subscript_vs_get():
    # Confusion=True; Expect Find=True; key=item
    # Subscript access should produce the same source-policy disagreement as .get().
    checked_item = request.form["item"] if "item" in request.form else None
    if not item_exists(checked_item):
        return jsonify({"error": "unknown item"}), 400

    ordered_item = request.args.get("item")
    return jsonify(place_order(ordered_item))


@bp.post("/find/header-vs-form")
def find_header_vs_form():
    # Confusion=True; Expect Find=True; key=account_id
    # Header account is authorized, but form account controls the loaded account.
    checked_account = request.headers.get("account_id")
    if checked_account != "allowed":
        return jsonify({"error": "account denied"}), 403

    effective_account = request.form.get("account_id")
    return jsonify(load_account(effective_account))


@bp.post("/find/cookie-vs-args")
def find_cookie_vs_args():
    # Confusion=True; Expect Find=True; key=theme
    # Cookie preference is checked, but query parameter controls the effective theme.
    checked_theme = request.cookies.get("theme")
    if checked_theme not in {"light", "dark"}:
        return jsonify({"error": "unsupported theme"}), 400

    effective_theme = request.args.get("theme")
    return jsonify(apply_theme(effective_theme))


# ============================================================================
# Confusion=False, Expect Find=False: true negatives CONF-001 should skip
# ============================================================================


@bp.post("/ignore/single-ternary-fallback")
def ignore_single_ternary_fallback():
    # Confusion=False; Expect Find=False; key=tip
    # One local fallback decision, one interpretation point.
    data = request.json if request.is_json else request.form
    tip = data.get("tip")
    return jsonify({"tip": tip})


@bp.post("/ignore/equivalent-reversed-ternary")
def ignore_equivalent_reversed_ternary():
    # Confusion=False; Expect Find=False; key=email
    # Same JSON/FORM policy, just written with the condition inverted.
    primary_data = request.json if request.is_json else request.form
    checked_email = primary_data.get("email")

    secondary_data = request.form if not request.is_json else request.json
    effective_email = secondary_data.get("email")

    return jsonify({"checked": checked_email, "effective": effective_email})


@bp.post("/ignore/same-source-two-sites")
def ignore_same_source_two_sites():
    # Confusion=False; Expect Find=False; key=name
    # Two sites, same key, same source policy.
    first_name = request.form.get("name")
    confirmed_name = request.form.get("name")
    return jsonify({"first": first_name, "confirmed": confirmed_name})


@bp.post("/ignore/same-source-different-accessor")
def ignore_same_source_different_accessor():
    # Confusion=False; Expect Find=False; key=name
    # Different accessor syntax on the same source is not source confusion.
    checked_name = request.form.get("name")
    effective_name = request.form["name"] if "name" in request.form else None
    return jsonify({"checked": checked_name, "effective": effective_name})


@bp.post("/ignore/different-keys-different-sources")
def ignore_different_keys_different_sources():
    # Confusion=False; Expect Find=False
    # Different logical inputs are not same-key input-source confusion.
    item = request.form.get("item")
    tip = request.args.get("tip")
    return jsonify({"item": item, "tip": tip})


@bp.post("/ignore/unrelated-json-and-form")
def ignore_unrelated_json_and_form():
    # Confusion=False; Expect Find=False
    # JSON and form coexist in one endpoint, but not for the same key.
    email = request.form.get("email")
    token = (
        request.json.get("token") if request.is_json and isinstance(request.json, dict) else None
    )
    return jsonify({"email": email, "token": token})


@bp.post("/ignore/helper-same-source")
def ignore_helper_same_source():
    # Confusion=False; Expect Find=False; key=item
    # Same helper reused twice with the same caller-visible policy.
    first_item = read_item(request.form)
    second_item = read_item(request.form)
    return jsonify({"first": first_item, "second": second_item})


@bp.post("/ignore/parameter-name-confusion-only")
def ignore_parameter_name_confusion_only():
    # Confusion=False; Expect Find=False
    # Parameter-name confusion belongs to CONF-002, not source disagreement.
    one_item = request.form.get("item")
    many_items = request.form.getlist("items")
    return jsonify({"item": one_item, "items": many_items})


@bp.post("/ignore/cardinality-confusion-only")
def ignore_cardinality_confusion_only():
    # Confusion=False; Expect Find=False
    # Cardinality confusion belongs to CONF-003, not source disagreement.
    first_item = request.form.get("items")
    all_items = request.form.getlist("items")
    return jsonify({"first": first_item, "all": all_items})


@bp.post("/ignore/values-and-form-different-keys")
def ignore_values_and_form_different_keys():
    # Confusion=False; Expect Find=False
    # request.values is only suspicious for CONF-001 when the same key disagrees.
    promo = request.values.get("promo")
    address = request.form.get("address")
    return jsonify({"promo": promo, "address": address})


# ============================================================================
# Confusion=False, Expect Find=True: false positives / known precision limits
# ============================================================================


@bp.post("/fp/explicit-if-else-fallback")
def fp_explicit_if_else_fallback():
    # Confusion=False; Expect Find=True; key=promo
    # Not confusion: one intentional JSON/FORM fallback written as branches.
    if request.is_json and isinstance(request.json, dict):
        promo = request.json.get("promo")
    else:
        promo = request.form.get("promo")
    return jsonify({"promo": promo})


@bp.post("/find/files-vs-form")
def find_files_vs_form():
    # Confusion=False; Expect Find=True; key=receipt
    # File/form disagreement exercises a less common Flask input source.
    checked_receipt = request.form.get("receipt")
    if checked_receipt != "declared":
        return jsonify({"error": "receipt metadata missing"}), 400

    effective_receipt = request.files.get("receipt")
    return jsonify(upload_receipt(effective_receipt))


@bp.route("/fp/method-based-split", methods=["GET", "POST"])
def fp_method_based_split():
    # Confusion=False; Expect Find=True; key=query
    # Not confusion: GET and POST are mutually exclusive request shapes.
    if request.method == "GET":
        query = request.args.get("query")
    else:
        query = request.form.get("query")
    return jsonify({"query": query})


@bp.post("/fp/defensive-consistency-check")
def fp_defensive_consistency_check():
    # Confusion=False; Expect Find=True; key=coupon
    # Not confusion: disagreement is explicitly detected and rejected.
    query_coupon = request.args.get("coupon")
    form_coupon = request.form.get("coupon")
    if query_coupon and form_coupon and query_coupon != form_coupon:
        return jsonify({"error": "coupon mismatch"}), 400
    return jsonify({"coupon": form_coupon or query_coupon})


@bp.post("/fp/helper-compare-and-reject")
def fp_helper_compare_and_reject():
    # Confusion=False; Expect Find=True; key=coupon
    # Not confusion: same defensive pattern, but helper-mediated.
    form_coupon = read_coupon(request.form)
    query_coupon = read_coupon(request.args)
    if form_coupon and query_coupon and form_coupon != query_coupon:
        return jsonify({"error": "conflicting coupon"}), 400
    return jsonify({"coupon": form_coupon or query_coupon})


@bp.post("/fp/logging-secondary-read")
def fp_logging_secondary_read():
    # Confusion=False; Expect Find=True; key=note
    # Not confusion: query value is telemetry only; form value drives behavior.
    query_note = request.args.get("note")
    actual_note = request.form.get("note")
    print("debug note from query:", query_note)
    return jsonify({"note": actual_note})


@bp.post("/fp/reject-ambiguous-dual-source")
def fp_reject_ambiguous_dual_source():
    # Confusion=False; Expect Find=True; key=api_key
    # Not confusion: code rejects requests that supply both sources.
    header_key = request.headers.get("api_key")
    form_key = request.form.get("api_key")
    if header_key and form_key:
        return jsonify({"error": "send api_key only once"}), 400
    return jsonify({"api_key": header_key or form_key})


@bp.post("/fp/debug-only-secondary-source")
def fp_debug_only_secondary_source():
    # Confusion=False; Expect Find=True; key=trace_id
    # Not confusion: query value is used only when explicit debug mode is enabled.
    trace_id = request.form.get("trace_id")
    if request.args.get("trace_id") and request.args.get("debug") == "1":
        print("debug trace override seen:", request.args.get("trace_id"))
    return jsonify({"trace_id": trace_id})


# ============================================================================
# Confusion=True, Expect Find=False: false negatives / expected misses
# ============================================================================


@bp.before_request
def middleware_literal_coupon_check():
    # Confusion=True; Expect Find=False; key=coupon
    # Real candidate: middleware checks query coupon, handler consumes form coupon.
    # Current limitation: CONF-001 is primarily handler-reachable.
    if request.path.endswith("/miss/middleware-vs-handler"):
        request.args.get("coupon")


@bp.post("/miss/middleware-vs-handler")
def miss_middleware_vs_handler():
    # Confusion=True; Expect Find=False; key=coupon
    coupon = request.form.get("coupon")
    return jsonify({"coupon": coupon})


@bp.before_request
def middleware_dynamic_parameter_check():
    # Confusion=True; Expect Find=False; key=amount
    # Real candidate: dynamic helper resolves amount from args/json/form.
    # Current limitation: literal key does not flow through parameter.
    if request.path.endswith("/miss/dynamic-helper-key"):
        get_request_parameter("amount")


@bp.post("/miss/dynamic-helper-key")
def miss_dynamic_helper_key():
    # Confusion=True; Expect Find=False; key=amount
    amount = request.form.get("amount")
    return jsonify({"amount": amount})


@bp.post("/miss/keyword-helper-argument")
def miss_keyword_helper_argument():
    # Confusion=True; Expect Find=False; key=keyword
    # Real candidate in principle: same helper receives form and values.
    # Current limitation: keyword argument propagation is not resolved precisely.
    validated = read_keyword_data(data=request.form)
    effective = read_keyword_data(data=request.values)
    return jsonify({"validated": validated, "effective": effective})


@bp.post("/miss/nested-helper-forwarding")
def miss_nested_helper_forwarding():
    # Confusion=True; Expect Find=False; key=nested
    # Real candidate in principle: policies disagree at the route callsites.
    # Current limitation: multi-hop parameter forwarding is not lifted back to
    # both caller-visible lines by CONF-001 site construction.
    validated = read_nested_outer(request.form)
    effective = read_nested_outer(request.values)
    return jsonify({"validated": validated, "effective": effective})


@bp.post("/miss/container-alias-flow")
def miss_container_alias_flow():
    # Confusion=True; Expect Find=False; key=container
    # Real candidate in principle, but source is hidden inside a container.
    sources = {"validated": request.form, "effective": request.values}
    validated = sources["validated"].get("container")
    effective = sources["effective"].get("container")
    return jsonify({"validated": validated, "effective": effective})
