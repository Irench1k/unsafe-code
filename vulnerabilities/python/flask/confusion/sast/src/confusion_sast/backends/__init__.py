"""Code analysis backends.

Available backends:
- ast: Pure Python AST analysis (no dependencies, fast, default)
- joern: Joern CPG server (requires joern CLI)
- codeql: CodeQL CLI (requires codeql CLI)
"""

from .ast_backend import ASTBackend
from .interface import Backend, ExtractionResult

__all__ = ["ASTBackend", "Backend", "ExtractionResult"]
