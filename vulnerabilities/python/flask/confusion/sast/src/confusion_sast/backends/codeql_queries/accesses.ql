/**
 * @name Flask request input accesses
 * @description Find accesses to Flask request input sources using Flask library models.
 *              Handles import aliases (e.g., `from flask import request as req`) and
 *              module-qualified access (e.g., `flask.request.args`) via the API graph.
 * @kind problem
 * @id confusion-sast/flask-request-accesses
 */

import python
import semmle.python.frameworks.Flask
import semmle.python.ApiGraphs
import semmle.python.dataflow.new.DataFlow

/** Valid Flask request input source attribute names. */
string requestSourceName() {
  result in ["args", "form", "values", "json", "data", "headers", "cookies", "files"]
}

from
  string access_repr, string source, string accessor, string key, string qualname, string file,
  int line
where
  // ---------- Pattern 1: method calls (.get / .getlist) on request attributes ----------
  // e.g. request.form.get("key"), req.args.getlist("items"), flask.request.json.get("x")
  exists(API::CallNode call, Function func |
    source = requestSourceName() and
    accessor in ["get", "getlist"] and
    call = Flask::request().getMember(source).getMember(accessor).getACall() and
    (
      key = call.getArg(0).asExpr().(StringLiteral).getText()
      or
      not call.getArg(0).asExpr() instanceof StringLiteral and key = "?"
    ) and
    func = call.asExpr().getScope() and
    access_repr = call.asExpr().toString() and
    qualname = func.getQualifiedName() and
    file = call.getLocation().getFile().getRelativePath() and
    line = call.getLocation().getStartLine()
  )
  or
  // ---------- Pattern 2: subscript access on request attributes ----------
  // e.g. request.form["key"], req.args["name"]
  exists(Subscript sub, Function func |
    source = requestSourceName() and
    sub.getObject() = Flask::request().getMember(source).asSource().asExpr() and
    accessor = "index" and
    (
      key = sub.getIndex().(StringLiteral).getText()
      or
      not sub.getIndex() instanceof StringLiteral and key = "?"
    ) and
    func = sub.getScope() and
    access_repr = sub.toString() and
    qualname = func.getQualifiedName() and
    file = sub.getLocation().getFile().getRelativePath() and
    line = sub.getLocation().getStartLine()
  )
  or
  // ---------- Pattern 3: bare attribute access on request ----------
  // e.g. request.form, request.args -- any reference to a request source object,
  // whether passed as a call argument, assigned to a variable, or used in-place.
  exists(Expr attrExpr, Function func |
    source = requestSourceName() and
    attrExpr = Flask::request().getMember(source).asSource().asExpr() and
    accessor = "direct" and
    key = "?" and
    func = attrExpr.getScope() and
    access_repr = attrExpr.toString() and
    qualname = func.getQualifiedName() and
    file = attrExpr.getLocation().getFile().getRelativePath() and
    line = attrExpr.getLocation().getStartLine()
  )
select access_repr, source, accessor, key, qualname, file, line
