The CodeQL upstream Flask and Werkzeug library models provide mature infrastructure for route detection, request source identification, type tracking through Werkzeug data structures, and response modeling. Our SAST tool can directly leverage upstream's route detection and request node resolution in our CodeQL queries, but cannot use upstream's taint tracking directly because it treats all request.\* attributes as fungible RemoteFlowSource (tainted but source-indistinguishable), whereas our entire value proposition requires distinguishing args from form from json. The report below catalogs every capability, identifies what to use, and specifies exactly how.

---

The research agent completed a thorough analysis of Flask.qll, Werkzeug.qll, FlaskAdmin.qll, FlaskSqlAlchemy.qll, and the experimental FlaskMail.qll. Here are the key findings:

What we leveraged from upstream (already implemented):

- Flask::request() API graph node in our rewritten accesses.ql now handles import aliases (from flask import request as req), module-qualified access (flask.request.args), and flask_restful.request for free
- Http::Server::RouteSetup gives us add_url_rule() and MethodView detection automatically

Where our implementation is ahead of upstream:

- Shorthand decorators (@bp.get(), @bp.post()) that we added to routes.ql are a gap in upstream's Flask model
- Our entire confusion detection domain (CONF-001 through CONF-007) has no upstream equivalent, because upstream's RemoteFlowSource abstraction erases source identity by design (it can't distinguish request.args from request.form)
- Our before_request detection, dict merge detection, and CombinedMultiDict precedence semantics are novel

What upstream models that we could use in future sessions:

- Werkzeug Authorization type tracking (request.authorization.username, .password, etc.) for auth header parsing confusion
- Werkzeug URL rule regex for extracting route parameters (enables route-parameter vs query-parameter confusion detection)
- InstanceTaintStepsHelper pattern that could inform a declarative refactor of the AST backend's source mapping
- Source-preserving taint tracking query (custom QL that tracks which request.\* attribute a value came from through assignments and function parameters)

---

Key Findings

A. Request Data Flow Models

A1. Flask Request Object Resolution

File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll:104-108

API::Node request() {
result = API::moduleImport(["flask", "flask_restful"]).getMember("request")
or
result = sessionInterfaceRequestParam()
}

This is the canonical way to get a reference to the Flask request object. It handles three paths:

1. from flask import request / flask.request
2. from flask_restful import request / flask_restful.request
3. The request parameter of SessionInterface.open_session() implementations

Our gap: Our accesses.ql at /Users/andrew/Projects/unsafe-code/vulnerabilities/python/flask/confusion/sast/src/confusion_sast/backends/codeql_queries/accesses.ql:16 does raw string matching:
attr.getObject().(Name).getId() = "request"
This misses flask_restful.request, aliased imports (from flask import request as req), and session interface request parameters. Switching to Flask::request() would fix all of these.

A2. Request Attribute Taint Steps

File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll:451-497

The InstanceTaintSteps class defines taint propagation for 30+ request attributes organized by type:

┌────────────────────────┬───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┐
│ Category │ Attributes │
├────────────────────────┼───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┤
│ String │ path, full_path, base_url, url, content_type, data, method, mimetype, origin, query_string, referrer, remote_addr, remote_user, user_agent │
├────────────────────────┼───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┤
│ Dict │ environ, cookies, mimetype_params, view_args │
├────────────────────────┼───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┤
│ JSON │ json │
├────────────────────────┼───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┤
│ List[str] │ access_route │
├────────────────────────┼───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┤
│ File-like │ stream, input_stream │
├────────────────────────┼───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┤
│ MultiDict │ args, values, form │
├────────────────────────┼───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┤
│ MultiDict[FileStorage] │ files │
├────────────────────────┼───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┤
│ Headers │ headers │
├────────────────────────┼───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┤
│ Authorization │ authorization │
├────────────────────────┼───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┤
│ Other │ accept_charsets, accept_encodings, accept_languages, accept_mimetypes, cache_control, pragma, access_control_request_headers │
└────────────────────────┴───────────────────────────────────────────────────────────────────────── 1 new message ↓ ──────────────────────────────────────────────────┘

Methods that propagate taint: get_data, get_json (Flask.qll:494) 1 new message ↓

Critical insight: Upstream marks ALL of these as tainted. It does NOT distinguish which source a va 1 new message ↓ is is the fundamental architectural mismatch -- our CONF-001 rule needs to know that request.args.get("key") and request.form.get("key") are different sources, but upstream's taint model collapses them both to "remote flow source."
1 new message ↓
A3. MultiDict Instance Tracking
1 new message ↓
File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll:499-503
1 new message ↓
private class RequestAttrMultiDict extends Werkzeug::MultiDict::InstanceSource {
RequestAttrMultiDict() { 1 new message ↓
this = request().getMember(["args", "values", "form", "files"]).asSource()
} 1 new message ↓
}
1 new message ↓
This registers request.args, request.values, request.form, and request.files as instances of Werkzeug::MultiDict, enabling taint propagation through MultiDict operations.
1 new message ↓
A4. MultiDict Taint Steps (Werkzeug)
1 new message ↓
File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Werkzeug.qll:55-65
1 new message ↓
private class InstanceTaintSteps extends InstanceTaintStepsHelper {
override string getMethodName() { result = "getlist" } 1 new message ↓
}
1 new message ↓
Important limitation: Upstream only explicitly models getlist as a taint-propagating method on MultiDict. The .get() method propagation comes from Python's general dict modeling elsewhere, NOT from the Werkzeug MultiDict model. Subscript access (dict[key]) is also handled generically. This means upstream does 1 new message ↓ .get() from .getlist() from [key] as different accessor kinds -- another dimension our tool needs that upstream does not provide.
1 new message ↓
A5. FileStorage Taint Steps
1 new message ↓
File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Werkzeug.qll:104-125
1 new message ↓
FileStorage attributes that propagate taint: filename, name, content_type, mimetype, stream, headers, mimetype_params.
1 new message ↓
File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll:505-519
1 new message ↓
Flask models how to reach FileStorage instances from request.files:

- request.files[key] (subscript) 1 new message ↓
- request.files.get(key) (method call return)
- request.files.getlist(key)[i] (list subscript after getlist) 1 new message ↓

A6. Headers Taint Steps 1 new message ↓

File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Werkzeug.qll:185-197 1 new message ↓

Headers methods that propagate taint: getlist, get_all, popitem, to_wsgi_list. 1 new message ↓

A7. Authorization Taint Steps 1 new message ↓

File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Werkzeug.qll:287-301 1 new message ↓

Authorization attributes that propagate taint: username, password, realm, nonce, uri, nc, cnonce, r 1 new message ↓ qop.

This is relevant for our confusion vulnerability analysis -- request.authorization is a parsed vers 1 new message ↓ ization header, and confusion between request.authorization.username and request.headers.get("Authorization") is a real vulnerability pattern.
1 new message ↓
B. Route Detection Models
1 new message ↓
B1. Flask Route Setup Hierarchy
1 new message ↓
File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll:335-356
1 new message ↓
The abstract class FlaskRouteSetup extends Http::Server::RouteSetup::Range and provides:

- URL pattern extraction using Werkzeug's route regex (Flask.qll:327-332) 1 new message ↓
- Routed parameter identification from URL patterns like <int:id> (Flask.qll:337-353)
- Framework identification as "Flask" 1 new message ↓

Three concrete implementations: 1 new message ↓

1. FlaskAppRouteCall (Flask.qll:363-375): @app.route() and @bp.route() decorators
2. FlaskAppAddUrlRuleCall (Flask.qll:382-406): app.add_url_rule() programmatic registration 1 new message ↓
3. FlaskViewClassHandlerWithoutKnownRoute (Flask.qll:409-430): View class methods without explicit route
   1 new message ↓
   B2. Decorator-based Route Detection
   1 new message ↓
   File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll:363-375
   1 new message ↓
   private class FlaskAppRouteCall extends FlaskRouteSetup, DataFlow::CallCfgNode {
   FlaskAppRouteCall() { 1 new message ↓
   this = FlaskApp::instance().getMember("route").getACall()
   or 1 new message ↓
   this = Blueprint::instance().getMember("route").getACall()
   } 1 new message ↓
   override Function getARequestHandler() { result.getADecorator().getAFlowNode() = node }
   } 1 new message ↓

This handles both Flask app instances and Blueprint instances. The handler is resolved by finding f 1 new message ↓ is call node appears as a decorator.

Our gap vs upstream: Our routes.ql already uses Http::Server::RouteSetup which captures FlaskAppRou 1 new message ↓ ion of shorthand route detection (@bp.get, @bp.post, etc.) at routes.ql:85-106 fills a gap that upstream does not handle (upstream only models .route()). This is an area where our implementation is ahead of upstream.
1 new message ↓
B3. add_url_rule() Detection
1 new message ↓
File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll:382-406
1 new message ↓
Upstream models app.add_url_rule(rule, endpoint, view_func) including resolution of the view function from:

1. Direct function references passed as view_func 1 new message ↓
2. View.as_view() results from Flask view classes
   1 new message ↓
   Our gap: Neither our AST backend nor our CodeQL queries detect add_url_rule(). The PLAN.md at line 141 identifies this. Our routes.ql gets this for free from upstream's Http::Server::RouteSetup, but our AST backend at /Users/andrew/Projects/unsafe-code/vulnerabilities/python/flask/confusion/sast/src/confu 1 new message ↓ s/ast_backend.py does not handle it.

B4. MethodView Class Detection 1 new message ↓

File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll:310-325 1 new message ↓

class FlaskMethodViewClass extends FlaskViewClass { 1 new message ↓
override Function getARequestHandler() {
result = super.getARequestHandler() 1 new message ↓
or
result = this.getAMethod() and 1 new message ↓
result.getName() = Http::httpVerbLower()
} 1 new message ↓
}
1 new message ↓
MethodView handlers are detected by finding methods named get, post, put, patch, delete, head, options on subclasses of flask.views.MethodView. This is a fully type-aware detection.
1 new message ↓
Our gap: Our AST backend does not detect MethodView handlers. Our CodeQL routes.ql gets this for free via the upstream FlaskViewClassHandlerWithoutKnownRoute class (Flask.qll:409-430).
1 new message ↓
B5. Blueprint Detection
1 new message ↓
File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll:88-101
1 new message ↓
Upstream models blueprints via:
API::moduleImport("flask").getMember("Blueprint") 1 new message ↓
or
API::moduleImport("flask").getMember("blueprints").getMember("Blueprint") 1 new message ↓

It tracks Blueprint class references and instances but does NOT model register_blueprint() composit 1 new message ↓ propagation. There is no upstream model for how blueprints compose into the full URL space.

B6. Flask-Admin Route Detection 1 new message ↓

File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/FlaskAdmin.qll:32-41 1 new message ↓

Flask-Admin @expose and @expose_plugview decorators are modeled as FlaskRouteSetup subclasses, mean 1 new message ↓ in Http::Server::RouteSetup queries.

C. Werkzeug-Specific Models 1 new message ↓

C1. Type Hierarchy 1 new message ↓

Upstream models four Werkzeug data structure types with the InstanceSource / instance() / InstanceT 1 new message ↓ :

┌───────────────┬──────────────────────┬─────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────────────────────────┐
│ Type │ File:Line │ Tainted Attributes │ Tainted Methods │
├───────────────┼──────────────────────┼─────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────────────────────────┤
│ MultiDict │ Werkzeug.qll:29-66 │ (none) │ getlist │
├───────────────┼──────────────────────┼─────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────────────────────────┤
│ FileStorage │ Werkzeug.qll:73-140 │ filename, name, content_type, mimetype, stream, headers, mimetype_params │ (none) │
├───────────────┼──────────────────────┼─────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────────────────────────┤
│ Headers │ Werkzeug.qll:147-253 │ (none) │ getlist, get_all, popitem, to_wsgi_list │
├───────────────┼──────────────────────┼─────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────────────────────────┤
│ Authorization │ Werkzeug.qll:260-302 │ username, password, realm, nonce, uri, nc, cnonce, response, opaque, qop │ (none) │
└───────────────┴──────────────────────┴─────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────────────────────────┘

Not modeled upstream: CombinedMultiDict, ImmutableMultiDict, TypeConversionDict, ImmutableOrderedMu 1 new message ↓ inedMultiDict is particularly relevant because request.values is a CombinedMultiDict that merges request.args and request.form with args taking precedence on key collision. Upstream treats request.values as a plain MultiDict, losing the precedence semantics that are central to our CONF-004 rule.
1 new message ↓
C2. TypeTracker Pattern for Instance Tracking
1 new message ↓
All four Werkzeug types use the same pattern for tracking instances through the data flow graph:
1 new message ↓
private DataFlow::TypeTrackingNode instance(DataFlow::TypeTracker t) {
t.start() and result instanceof InstanceSource 1 new message ↓
or
exists(DataFlow::TypeTracker t2 | result = instance(t2).track(t2, t)) 1 new message ↓
}
DataFlow::Node instance() { instance(DataFlow::TypeTracker::end()).flowsTo(result) } 1 new message ↓

This is a recursive type-tracking predicate that follows values from their creation (InstanceSource 1 new message ↓ ents, function calls, and other data flow steps. This is substantially more powerful than our AST backend's simple alias tracking (which only follows x = request.form one level deep) and our Joern backend's pattern matching on code strings.
1 new message ↓
C3. Headers Response Write Modeling
1 new message ↓
File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Werkzeug.qll:199-253
1 new message ↓
Upstream models response header writes through:

- Method calls: add, add_header, set, setdefault, **setitem** 1 new message ↓
- Subscript assignment: headers["key"] = "value"
- Bulk operations: headers.extend(dict) 1 new message ↓

Each write records whether newlines are allowed in names/values (for header injection detection). 1 new message ↓

D. Security Sink Models 1 new message ↓

D1. Upstream Sink Categories 1 new message ↓

From /Users/andrew/src/codeql/python/ql/lib/semmle/python/Concepts.qll: 1 new message ↓

┌────────────────────────────────┬──────────────────────┬────────────────────────────────────────── 1 new message ↓ ───┐
│ Concept │ File:Line │ Flask Connection │
├────────────────────────────────┼──────────────────────┼────────────────────────────────────────── 1 new message ↓ ───┤
│ SystemCommandExecution │ Concepts.qll:85-109 │ No Flask-specific sinks │
├────────────────────────────────┼──────────────────────┼────────────────────────────────────────── 1 new message ↓ ───┤
│ FileSystemAccess │ Concepts.qll:118-156 │ flask.send_from_directory, flask.send_file, FileStorage.save │
├────────────────────────────────┼──────────────────────┼────────────────────────────────────────── 1 new message ↓ ───┤
│ SqlConstruction / SqlExecution │ Concepts.qll:400-464 │ Via FlaskSqlAlchemy.qll │
├────────────────────────────────┼──────────────────────┼────────────────────────────────────────── 1 new message ↓ ───┤
│ CodeExecution │ Concepts.qll:380-398 │ No Flask-specific sinks │
├────────────────────────────────┼──────────────────────┼────────────────────────────────────────── 1 new message ↓ ───┤
│ TemplateConstruction │ Concepts.qll:897-915 │ flask.render_template_string, flask.stream_template_string │
├────────────────────────────────┼──────────────────────┼────────────────────────────────────────── 1 new message ↓ ───┤
│ Escaping │ Concepts.qll:780-849 │ No Flask-specific sinks │
├────────────────────────────────┼──────────────────────┼────────────────────────────────────────── 1 new message ↓ ───┤
│ Decoding │ Concepts.qll:243-294 │ No Flask-specific sinks │
└────────────────────────────────┴──────────────────────┴────────────────────────────────────────── 1 new message ↓ ───┘

D2. No Authorization/Authentication Models 1 new message ↓

Upstream has NO models for: 1 new message ↓

- Authorization bypass patterns
- Authentication confusion patterns 1 new message ↓
- Role-based access control
- Session fixation 1 new message ↓
- CSRF protection state (there IS CsrfProtectionSetting at Concepts.qll:1595 but it's about CSRF toggle detection, not confusion)
  1 new message ↓
  This is the entire domain our tool operates in. Upstream is focused on injection-class vulnerabilities (SQLi, XSS, command injection, path traversal). Our confusion vulnerability detection is novel territory with no upstream equivalent. 1 new message ↓

E. Code Patterns and Approaches 1 new message ↓

E1. API Graph Pattern 1 new message ↓

File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll (throughout) 1 new message ↓

The API::Node graph pattern is the backbone of all upstream Flask modeling: 1 new message ↓

API::moduleImport("flask").getMember("Flask") // flask.Flask class 1 new message ↓
API::moduleImport("flask").getMember("Flask").getReturn() // flask.Flask() instance
instance.getMember("route").getACall() // @app.route() call 1 new message ↓

This pattern provides: 1 new message ↓

- Import-insensitive matching (handles from flask import Flask and import flask; flask.Flask)
- Chained member access with full qualification 1 new message ↓
- Return value and subclass tracking
  1 new message ↓
  Our CodeQL queries partially use this (via Http::Server::RouteSetup in routes.ql) but our accesses.ql does NOT use it at all, falling back to raw AST name matching.
  1 new message ↓
  E2. InstanceTaintStepsHelper Decomposition
  1 new message ↓
  File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/internal/InstanceTaintStepsHelper.qll:15-27
  1 new message ↓
  The InstanceTaintStepsHelper abstract class provides a clean three-way decomposition:
  1 new message ↓
  ┌────────────────────┬────────────────────────────────────────────┐
  │ Override │ Semantics │ 1 new message ↓
  ├────────────────────┼────────────────────────────────────────────┤
  │ getInstance() │ What nodes are instances of this type? │ 1 new message ↓
  ├────────────────────┼────────────────────────────────────────────┤
  │ getAttributeName() │ Which attribute accesses propagate taint? │ 1 new message ↓
  ├────────────────────┼────────────────────────────────────────────┤
  │ getMethodName() │ Which method call results propagate taint? │ 1 new message ↓
  └────────────────────┴────────────────────────────────────────────┘
  1 new message ↓
  The InstanceAdditionalTaintStep class at line 29-51 then generates taint steps automatically from these declarations.
  1 new message ↓
  Adaptable pattern: This decomposition maps directly to our InputSource + AccessorKind model. Our AST backend uses ad-hoc if/elif chains in \_resolve_input_source() (ast_backend.py:288-300) and \_check_input_access_call() (ast_backend.py:302-337). These could be systematized into a declarative 1 new message ↓ ing InstanceTaintStepsHelper.

E3. Werkzeug Rule Regex 1 new message ↓

File: /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll:327-332 1 new message ↓

private string werkzeug*rule_re() { 1 new message ↓
result =
"(?<static>[^<]\*)<(?:(?<converter>[a-zA-Z*][a-zA-Z0-9_]_)(?:\\((?<args>._?)\\))?\\:)?(?<var 1 new message ↓ -zA-Z0-9\_]\*)>"
}
1 new message ↓
This regex parses Werkzeug URL rules to extract route parameters (e.g., <int:id> -> variable=id, converter=int). Our AST backend does not parse URL rule parameters at all.
1 new message ↓
F. Blueprint and Application Structure
1 new message ↓
F1. What IS Modeled
1 new message ↓

- Flask app class and instances (Flask.qll:73-82)
- Blueprint class and instances (Flask.qll:88-101) 1 new message ↓
- Route registration on both apps and blueprints (Flask.qll:363-375)
- add_url_rule() on both apps and blueprints (Flask.qll:382-406) 1 new message ↓
- Flask-Admin expose and expose_plugview (FlaskAdmin.qll)
  1 new message ↓
  F2. What is NOT Modeled
  1 new message ↓
- register_blueprint() calls (no composition tracking)
- URL prefix composition (url_prefix="/api") 1 new message ↓
- before_request / after_request / teardown_request hooks
- before_app_request (global hooks via blueprint) 1 new message ↓
- Error handlers (@app.errorhandler)
- Context processors 1 new message ↓
- Blueprint grouping / nesting (Flask 2.0+)
  1 new message ↓
  The lack of before_request modeling is significant for our tool -- our CONF-006 rule detects middleware/handler source divergence, and CodeQL cannot directly help with detecting before_request registrations.
  1 new message ↓

---

Architecture Assessment: Upstream vs Our Implementation 1 new message ↓

Where Upstream is Stronger 1 new message ↓

┌─────────────────────────┬───────────────────────────────────────────────────────────────┬──────── 1 new message ↓ ───────┬───────────────────────────────────────────────────────────────────────────────────────── ──┐
│ Area │ Upstream │ 1 new message ↓ │ Impact │
├─────────────────────────┼───────────────────────────────────────────────────────────────┼──────── 1 new message ↓ ───────┼───────────────────────────────────────────────────────────────────────────────────────── ──┤
│ Request node resolution │ API graph with import aliases, flask_restful, session │ Raw Nam 1 new message ↓ est" │ Our accesses.ql misses aliased/alternative imports │
│ │ interface │ 1 new message ↓ │ │
├─────────────────────────┼───────────────────────────────────────────────────────────────┼──────── 1 new message ↓ ───────┼───────────────────────────────────────────────────────────────────────────────────────── ──┤
│ Type tracking │ TypeTracker follows values through assignments, calls, │ One-lev 1 new message ↓ in │ We miss multi-hop aliases like d = get_data(); d.get(k) where get_data() returns │
│ │ returns │ AST 1 new message ↓ │ request.form │
├─────────────────────────┼───────────────────────────────────────────────────────────────┼──────── 1 new message ↓ ───────┼───────────────────────────────────────────────────────────────────────────────────────── ──┤
│ add_url_rule() │ Fully modeled with view function resolution │ Not imp 1 new message ↓ │ We miss programmatic route registration │
│ detection │ │ 1 new message ↓ │ │
├─────────────────────────┼───────────────────────────────────────────────────────────────┼──────── 1 new message ↓ ───────┼───────────────────────────────────────────────────────────────────────────────────────── ──┤
│ MethodView detection │ Fully modeled with HTTP verb method mapping │ Not imp 1 new message ↓ │ We miss class-based view handlers │
├─────────────────────────┼───────────────────────────────────────────────────────────────┼──────── 1 new message ↓ ───────┼───────────────────────────────────────────────────────────────────────────────────────── ──┤
│ FileStorage taint │ Models .filename, .name, subscript, .get(), .getlist() │ Not mod 1 new message ↓ │ Not relevant to confusion detection │
│ │ returns │ 1 new message ↓ │ │
├─────────────────────────┼───────────────────────────────────────────────────────────────┼──────── 1 new message ↓ ───────┼───────────────────────────────────────────────────────────────────────────────────────── ──┤
│ URL parameter │ Werkzeug regex parsing extracts <converter:variable> │ Not imp 1 new message ↓ │ Could help detect route parameter vs query parameter confusion │
│ extraction │ │ 1 new message ↓ │ │
└─────────────────────────┴───────────────────────────────────────────────────────────────┴──────── 1 new message ↓ ───────┴───────────────────────────────────────────────────────────────────────────────────────── ──┘
1 new message ↓
Where Our Implementation is Stronger
1 new message ↓
┌───────────────────────────────────┬──────────────────────────────────────────────────────────┬────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────────── ─┐ 1 new message ↓
│ Area │ Ours │ Upstream │ Impact │ 1 new message ↓
├───────────────────────────────────┼──────────────────────────────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────── ─┤ 1 new message ↓
│ Source discrimination │ Tracks WHICH request.\* attribute data came from │ All sources collapse to RemoteFlowSource │ Core value proposition -- upstream cannot do confusion │ 1 new message ↓
│ │ │ │ detection │ 1 new message ↓
├───────────────────────────────────┼──────────────────────────────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────── ─┤ 1 new message ↓
│ Accessor discrimination │ Distinguishes .get() vs .getlist() vs [key] │ No distinction │ Enables CONF-003 (cardinality confusion) │ 1 new message ↓
├───────────────────────────────────┼──────────────────────────────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────── ─┤ 1 new message ↓
│ Shorthand decorators │ routes.ql detects @bp.get(), @bp.post(), etc. │ Not modeled │ Better coverage of modern Flask patterns │ 1 new message ↓
├───────────────────────────────────┼──────────────────────────────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────── ─┤ 1 new message ↓
│ before_request detection │ AST backend detects decorator-based registration │ Not modeled │ Enables CONF-006 (middleware divergence) │ 1 new message ↓
├───────────────────────────────────┼──────────────────────────────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────── ─┤ 1 new message ↓
│ Dict merge detection │ AST detects {**a, **b} patterns │ Not modeled │ Enables CONF-005 (dict merge overwrite) │ 1 new message ↓
├───────────────────────────────────┼──────────────────────────────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────── ─┤ 1 new message ↓
│ CombinedMultiDict semantics │ CONF-004 encodes args-over-form precedence │ Treated as plain MultiDict │ Our CONF-004 is novel │ 1 new message ↓
├───────────────────────────────────┼──────────────────────────────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────── ─┤ 1 new message ↓
│ Interprocedural source │ AST propagates source identity through call edges │ Taint propagates but source identity lost │ Enables finding confusion in helper functions │ 1 new message ↓
│ propagation │ │ │ │ 1 new message ↓
├───────────────────────────────────┼──────────────────────────────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────── ─┤ 1 new message ↓
│ Conditional source selection │ Detects request.json if request.is_json else │ Not modeled │ Enables CONF-007 │ 1 new message ↓
│ │ request.form │ │ │ 1 new message ↓
├───────────────────────────────────┼──────────────────────────────────────────────────────────┼────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────────── ─┤ 1 new message ↓
│ flask_restful.request │ Flask::request() at Flask.qll:105 includes it │ Our accesses.ql misses it, but upstream includes │ Upstream is ahead but we should use it │ 1 new message ↓
│ │ │ it │ │ 1 new message ↓
└───────────────────────────────────┴──────────────────────────────────────────────────────────┴────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────────── ─┘ 1 new message ↓

--- 1 new message ↓
Concrete Recommendations
1 new message ↓

1. Replace raw request matching in accesses.ql with upstream Flask::request()
   1 new message ↓
   Current (accesses.ql:16):
   attr.getObject().(Name).getId() = "request" 1 new message ↓

Target: Import and use Flask::request() from the upstream Flask.qll library. This requires restruct 1 new message ↓ to use the API graph pattern:

import semmle.python.frameworks.Flask 1 new message ↓

// Use Flask::request() to match all forms of the request object 1 new message ↓
Flask::request().getMember(["args", "form", "values", "json", ...]).asSource()
1 new message ↓
This single change would fix: aliased imports, flask_restful.request, and session interface request parameters.
1 new message ↓ 2. Write a source-preserving taint tracking query for aliased accesses
1 new message ↓
Upstream's InstanceTaintSteps propagates taint but loses source identity. Write a custom query that:

- Sources: Flask::request().getMember("args"), Flask::request().getMember("form"), etc. -- each tag 1 new message ↓ tSource
- Sinks: .get(), .getlist(), subscript on any node reachable from a source
- Track source identity through local assignments and function parameters 1 new message ↓
- Emit (source_type, accessor_type, key, function_qualname) tuples
  1 new message ↓
  This is the most impactful CodeQL improvement. It would give the CodeQL backend the same aliased-access detection that the AST backend achieves through its \_request_aliases dict and \_propagate_sources method, but with CodeQL's type-aware data flow. 1 new message ↓

3. Leverage upstream for add_url_rule() and MethodView route detection 1 new message ↓

Our routes.ql already uses Http::Server::RouteSetup, which automatically captures upstream's FlaskA 1 new message ↓ and FlaskViewClassHandlerWithoutKnownRoute classes. Verify that our \_query_routes Python parser (codeql_backend.py:209-237) handles these result formats correctly. It should, since all route types produce handler functions with locations.
1 new message ↓
For the AST backend, add add_url_rule() pattern matching to \_analyze_decorators in ast_backend.py. For MethodView, add class-level analysis that identifies methods named after HTTP verbs on subclasses of MethodView. 1 new message ↓

4. Adopt the InstanceTaintStepsHelper pattern in the AST backend 1 new message ↓

Refactor \_INPUT_SOURCE_MAP, \_resolve_input_source(), and \_check_input_access_call() in ast_backend. 1 new message ↓ tive structure:

@dataclass 1 new message ↓
class FlaskRequestModel:
source: InputSource 1 new message ↓
attribute: str # "args", "form", "json", etc.
dict_like: bool # supports .get(), .getlist(), [key] 1 new message ↓
methods: list[str] # additional taint methods ("get_json", etc.)
1 new message ↓
This makes it trivial to add new sources (e.g., request.authorization.username as a sub-source of HEADERS) without modifying control flow.
1 new message ↓ 5. Add flask_restful.request to all backends
1 new message ↓
Upstream handles this at Flask.qll:105. Our AST backend should check for from flask_restful import request in addition to from flask import request. Our Joern backend's pattern matching on request.args etc. would naturally catch this if the variable is named request. 1 new message ↓

6. Add Werkzeug URL rule parameter parsing to the AST backend 1 new message ↓

Use a Python translation of the Werkzeug rule regex from Flask.qll:327-332 to extract route paramet 1 new message ↓ a new detection rule: route parameter vs query parameter confusion (e.g., /users/<user_id> where user_id is also read from request.args).
1 new message ↓ 7. Model request.authorization as a specialized source
1 new message ↓
Upstream models request.authorization as a Werkzeug Authorization instance with tainted attributes username, password, etc. (Werkzeug.qll:287-301, Flask.qll:527-529). We should add InputSource.AUTHORIZATION to our model or treat request.authorization.username as a specific accessor pattern on InputSource.HEADER 1 new message ↓ tion of auth header parsing confusion.

8. Do NOT try to upstream our confusion detection rules 1 new message ↓

Upstream's architecture fundamentally cannot support confusion detection without a new concept. The 1 new message ↓ abstraction erases source identity by design. Our detection rules (CONF-001 through CONF-007) are novel and should remain in our custom query pack. What we CAN upstream is the shorthand decorator detection in routes.ql -- it fills a genuine gap in upstream's route modeling.
1 new message ↓

---

Implementation Map 1 new message ↓

┌────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┬───────────────────────┬──────────────────────────────────────────────────── ───┐
│ File 1 new message ↓ │ Purpose │ Key Contents │
├────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┼───────────────────────┼──────────────────────────────────────────────────── ───┤
│ /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Flask.qll 1 new message ↓ │ Flask framework model │ Request node, route setup, response, taint steps, │
│ 1 new message ↓ │ │ template sinks │
├────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┼───────────────────────┼──────────────────────────────────────────────────── ───┤
│ /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/Werkzeug.qll 1 new message ↓ │ Werkzeug data │ MultiDict, FileStorage, Headers, Authorization type │
│ 1 new message ↓ │ structures │ tracking │
├────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┼───────────────────────┼──────────────────────────────────────────────────── ───┤
│ /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/FlaskAdmin.qll 1 new message ↓ │ Flask-Admin routes │ @expose and @expose_plugview as RouteSetup subclasses │
├────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┼───────────────────────┼──────────────────────────────────────────────────── ───┤
│ /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/FlaskSqlAlchemy.qll 1 new message ↓ │ Flask-SQLAlchemy │ db.session, db.text(), db.engine as SQLAlchemy entry │
│ 1 new message ↓ │ │ points │
├────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┼───────────────────────┼──────────────────────────────────────────────────── ───┤
│ /Users/andrew/src/codeql/python/ql/src/experimental/semmle/python/libraries/FlaskMail.qll 1 new message ↓ │ Flask-Mail │ Email sending API with body, recipient, sender │
│ 1 new message ↓ │ │ extraction │
├────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┼───────────────────────┼──────────────────────────────────────────────────── ───┤
│ /Users/andrew/src/codeql/python/ql/lib/semmle/python/Concepts.qll 1 new message ↓ │ HTTP concept │ RouteSetup, HttpResponse, ResponseHeaderWrite, │
│ 1 new message ↓ │ interfaces │ CookieWrite, CSRF │
├────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┼───────────────────────┼──────────────────────────────────────────────────── ───┤
│ /Users/andrew/src/codeql/python/ql/lib/semmle/python/frameworks/internal/InstanceTaintStepsHelper 1 new message ↓ │ Taint step helper │ Declarative attribute/method taint propagation │
├────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┼───────────────────────┼──────────────────────────────────────────────────── ───┤
│ /Users/andrew/Projects/unsafe-code/vulnerabilities/python/flask/confusion/sast/src/confusion_sast 1 new message ↓ queries/accesses.ql │ Our access query │ Highest priority fix: replace raw name matching with │
│ 1 new message ↓ │ │ Flask::request() │
├────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┼───────────────────────┼──────────────────────────────────────────────────── ───┤
│ /Users/andrew/Projects/unsafe-code/vulnerabilities/python/flask/confusion/sast/src/confusion_sast 1 new message ↓ queries/routes.ql │ Our route query │ Already good; shorthand detection is ahead of │
│ 1 new message ↓ │ │ upstream │
├────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┼───────────────────────┼──────────────────────────────────────────────────── ───┤
│ /Users/andrew/Projects/unsafe-code/vulnerabilities/python/flask/confusion/sast/src/confusion_sast 1 new message ↓ kend.py │ AST backend │ Needs MethodView, add_url_rule, declarative refactor │
└────────────────────────────────────────────────────────────────────────────────────────────────── 1 new message ↓ ────────────────────┴───────────────────────┴──────────────────────────────────────────────────── ───┘
1 new message ↓
Build Sequence
1 new message ↓
Fix accesses.ql to use Flask::request() -- Highest ROI. Single change that fixes aliased imports, flask_restful, and session interface coverage. Requires only importing Flask.qll and using the API graph pattern instead of raw name matching. 1 new message ↓
Write source-preserving taint tracking query -- New query file (tainted_accesses.ql) that tracks source identity through assignments and function parameters using CodeQL's data flow. This replaces the need for AST augmentation when running the CodeQL backend. 1 new message ↓
Add MethodView detection to AST backend -- Walk class definitions, check for MethodView in base classes, register HTTP-verb-named methods as request handlers.
Add add_url_rule() detection to AST backend -- Pattern match on app.add_url_rule(rule, endpoint, vi 1 new message ↓ module-level code.
Refactor AST backend to declarative source model -- Replace ad-hoc pattern matching with a FlaskRequestModel registry. This parallels upstream's InstanceTaintStepsHelper pattern and makes adding new sources trivial. 1 new message ↓
Add URL parameter parsing -- Port the Werkzeug route regex from Flask.qll:327-332 to Python. Enable detection of route-parameter vs query-parameter confusion.
Add request.authorization modeling -- New InputSource or sub-source for parsed authorization data. 1 new message ↓
Add flask_restful.request to AST and Joern backends -- Trivial: check for the alternative import path.
1 new message ↓
Risks
1 new message ↓
┌────────────────────────────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Risk │ 1 new message ↓ Mitigation │
├────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Source-preserving taint tracking query may be slow │ Start with local-scope tracking (sam 1 new message ↓ nd to interprocedural only if needed. Profile query evaluation time. │
├────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Flask::request() may not resolve in all import patterns │ Verify against our test corpus. If i 1 new message ↓ the raw name check caught, add them as fallback. │
├────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ MethodView detection in AST requires base class resolution │ Use simple string matching on class 1 new message ↓ names first. Full MRO resolution is not needed for our corpus. │
├────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ CodeQL database creation is slow (~30s per project) │ Already accepted cost. Source-preser 1 new message ↓ s to query time but not DB creation time. │
├────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Upstream API may change between CodeQL releases │ Pin codeql/python-all version in qlp 1 new message ↓ f using "\*". │
└────────────────────────────────────────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
