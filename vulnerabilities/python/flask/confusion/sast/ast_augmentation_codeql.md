AST Augmentation vs CodeQL Dataflow: Long-term Analysis

Having read _propagate_sources() in the AST backend (lines 808-897) and the overall architecture, here's my assessment:

What AST _propagate_sources() does well

It performs fixed-point iteration over explicit call edges, resolving chains like f(request.form) → g(data) → data.get("key"). This handles the core Flask pattern where request objects are passed as function arguments. It uses argument_map on CallEdge to track which argument position receives which source, then iterates until convergence (max 5 iterations, which covers deeply nested forwarding chains).

Specific limitations of the AST approach

1. Aliased references break source tracking:
# AST can't track this:
src = request.form
data = src
value = data.get("key")  # source identity lost at assignment

The AST backend only resolves when request.form appears directly in a call argument. If a variable alias sits between the request access and the function call, _code_to_input_source() won't match it.

2. Indirect dispatch is invisible:
# Dict of validators - AST can't follow this
validators = {"admin": check_admin, "user": check_user}
validators[role](request.form)  # call edge not recorded

3. Dynamic attribute access is opaque:
source_name = "form"
data = getattr(request, source_name)  # AST sees getattr, not request.form

4. Decorator-wrapped functions can confuse call graph construction. The AST backend handles Flask decorators specifically, but custom decorator patterns that wrap functions may not establish correct call edges.

5. Class-based views with method dispatch:
class OrderView(MethodView):
    def post(self):  # AST may not connect this to the route
        data = request.form

What CodeQL dataflow would provide

CodeQL's dataflow configuration with labeled sources would track taint through:
- Local variable assignments (x = request.form; x.get("key"))
- Field stores and loads (attribute assignments on objects)
- Return value propagation across function boundaries
- Type-based virtual dispatch resolution

A CodeQL TaintTracking::Configuration with isSource predicates for each InputSource and isSink at .get() / [] / .getlist() calls would give you automatic inter-procedural tracking without needing the manual_propagate_sources iteration.

Where CodeQL still falls short for this use case

CodeQL's Python analysis has its own gaps:
- Flask blueprint patterns require custom modeling (CodeQL ships some Flask models, but they don't cover all patterns you use)
- Dict unpacking ({**a, **b}) ordering semantics aren't tracked by standard dataflow
- Singular/plural heuristics (CONF-002) are string-level reasoning that CodeQL has no native support for
- Middleware/handler divergence (CONF-006) requires cross-function comparison logic that's awkward in QL

The pragmatic assessment

For your current use case (Flask apps with direct request.form / request.args patterns), the AST approach covers 90%+ of realistic code. The gaps (aliased references, indirect dispatch) rarely appear in Flask route handlers because developers typically access request data directly or pass it as explicit arguments.

Where it matters for scaling: If you apply this to larger Flask codebases where helper libraries wrap request access behind abstractions, the aliased-reference gap becomes real. A codebase that does data =get_request_data() where get_request_data() returns request.form would be invisible to the AST backend.

Concrete recommendations

Don't rewrite to CodeQL now. The multi-backend architecture already insulates you from any single backend's limitations.
Extend AST source propagation to handle simple aliasing. Track x = request.form assignments within function scope and resolve x.get("key") to InputSource.FORM. This is ~50 lines of AST visitor code and closes the biggest gap.
Add a CodeQL-specific source propagation pass when the CodeQL backend is used. Rather than replacing the AST approach, add a CodeQL query that outputs (function, param_idx, source_label) tuples, which the existing_propagate_sources infrastructure can consume.
Use the Chimera backend as your gold standard. It already combines AST + Joern + CodeQL, so you get the best of all worlds for coverage testing.
