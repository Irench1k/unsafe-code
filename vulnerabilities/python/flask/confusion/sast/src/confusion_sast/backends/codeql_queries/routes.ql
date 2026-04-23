/**
 * @name Flask route handlers
 * @description Find all Flask route handler functions with their URL patterns and HTTP methods
 * @kind problem
 * @id confusion-sast/flask-routes
 */

import python
import semmle.python.Concepts
import semmle.python.dataflow.new.DataFlow

/**
 * Gets a single HTTP method string from the methods= keyword argument of
 * a Flask RouteSetup decorator. Handles both list and tuple literals.
 */
string getRouteMethod(Http::Server::RouteSetup setup) {
  result =
    setup
        .(DataFlow::CallCfgNode)
        .getArgByName("methods")
        .getALocalSource()
        .asExpr()
        .(List)
        .getAnElt()
        .(StringLiteral)
        .getText()
  or
  result =
    setup
        .(DataFlow::CallCfgNode)
        .getArgByName("methods")
        .getALocalSource()
        .asExpr()
        .(Tuple)
        .getAnElt()
        .(StringLiteral)
        .getText()
}

/**
 * Gets the HTTP method for a shorthand decorator (@bp.get, @bp.post, etc.)
 * by mapping the attribute name to its uppercase HTTP method.
 */
string getShorthandMethod(string attr_name) {
  attr_name = "get" and result = "GET"
  or
  attr_name = "post" and result = "POST"
  or
  attr_name = "put" and result = "PUT"
  or
  attr_name = "patch" and result = "PATCH"
  or
  attr_name = "delete" and result = "DELETE"
}

/**
 * Holds when `handler` is registered via a standard Flask RouteSetup
 * (detected by the CodeQL Flask library model).
 */
predicate isLibraryRoute(
  Function handler, string name, string qualname, string file, int line, string url,
  string method
) {
  exists(Http::Server::RouteSetup setup |
    handler = setup.getARequestHandler() and
    setup.getFramework() = "Flask" and
    name = handler.getName() and
    qualname = handler.getQualifiedName() and
    file = handler.getLocation().getFile().getRelativePath() and
    line = handler.getLocation().getStartLine() and
    url = setup.getUrlPattern() and
    (
      method = getRouteMethod(setup)
      or
      not exists(getRouteMethod(setup)) and method = ""
    )
  )
}

/**
 * Holds when `handler` is registered via a shorthand decorator like
 * @bp.get("/path") or @app.post("/path") that the Flask library model
 * does not detect.
 */
predicate isShorthandRoute(
  Function handler, string name, string qualname, string file, int line, string url,
  string method
) {
  not exists(Http::Server::RouteSetup setup | handler = setup.getARequestHandler()) and
  exists(Call dec, Attribute attr, string attr_name |
    dec = handler.getADecorator() and
    attr = dec.getFunc() and
    attr_name = attr.getName() and
    attr_name in ["get", "post", "put", "patch", "delete"] and
    name = handler.getName() and
    qualname = handler.getQualifiedName() and
    file = handler.getLocation().getFile().getRelativePath() and
    line = handler.getLocation().getStartLine() and
    method = getShorthandMethod(attr_name) and
    (
      url = dec.getArg(0).(StringLiteral).getText()
      or
      not dec.getArg(0) instanceof StringLiteral and url = ""
    )
  )
}

from Function handler, string name, string qualname, string file, int line, string url, string method
where
  isLibraryRoute(handler, name, qualname, file, line, url, method)
  or
  isShorthandRoute(handler, name, qualname, file, line, url, method)
select handler,
  name,
  qualname,
  file,
  line,
  url,
  method
