/**
 * @name Call graph edges
 * @description Extract function call relationships within the project
 * @kind problem
 * @id confusion-sast/call-edges
 */

import python

from Call call, Function caller
where
  caller = call.getScope() and
  caller.inSource()
select caller.getQualifiedName(),
  call.getFunc().toString(),
  call.getLocation().getFile().getRelativePath(),
  call.getLocation().getStartLine()
