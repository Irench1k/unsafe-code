"""Language-specific parsing and configuration."""

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

try:
    import esprima  # type: ignore
except Exception:  # pragma: no cover - optional import
    esprima = None  # Fallback handled in JS parser

from .models import ExamplePart


@dataclass
class LanguageConfig:
    """Configuration for a supported language."""
    name: str
    extensions: set[str]
    function_parser: 'FunctionParser'


class FunctionParser(ABC):
    """Abstract base class for language-specific function boundary detection."""

    @abstractmethod
    def find_function_end(self, lines: list[str], start_line_1b: int) -> int:
        """Find the end line of a function starting at start_line_1b (1-based).

        Args:
            lines: File content as list of lines
            start_line_1b: Starting line number (1-based) right after @/unsafe marker

        Returns:
            End line number (1-based, inclusive) of the function
        """
        pass


class PythonFunctionParser(FunctionParser):
    """Parser for Python function boundaries using AST with indentation fallback."""

    def _find_function_end_ast(self, lines: list[str], start_line_1b: int) -> int | None:
        try:
            source = "\n".join(lines)
            tree = ast.parse(source)
            candidates: list[ast.AST] = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and getattr(node, "lineno", 0) >= start_line_1b:
                    candidates.append(node)
            if not candidates:
                return None
            # Choose the earliest function starting at or after start_line
            target = min(candidates, key=lambda n: getattr(n, "lineno", 10**9))
            end_lineno = getattr(target, "end_lineno", None)
            if end_lineno is not None:
                return int(end_lineno)
            return None
        except (SyntaxError, ValueError):
            return None

    def _find_function_end_indentation(self, lines: list[str], start_line_1b: int) -> int:
        n = len(lines)
        i = max(0, start_line_1b - 1)
        # Find the next 'def' or 'async def'
        while i < n:
            stripped = lines[i].lstrip()
            if stripped.startswith("def ") or stripped.startswith("async def "):
                break
            i += 1
        if i >= n:
            return max(1, start_line_1b)
        base_indent = len(lines[i]) - len(lines[i].lstrip(" "))
        j = i + 1
        last_content = i
        while j < n:
            line = lines[j]
            stripped = line.lstrip()
            if not stripped:
                j += 1
                continue
            current_indent = len(line) - len(stripped)
            if current_indent <= base_indent:
                break
            last_content = j
            j += 1
        return last_content + 1

    def find_function_end(self, lines: list[str], start_line_1b: int) -> int:
        end_ast = self._find_function_end_ast(lines, start_line_1b)
        if end_ast is not None:
            return end_ast
        return self._find_function_end_indentation(lines, start_line_1b)


class JavaScriptFunctionParser(FunctionParser):
    """Parser for JavaScript/TypeScript function boundaries using esprima with brace fallback."""

    def _walk_js_ast(self, node):
        if hasattr(node, 'type'):
            yield node
        for _key, value in vars(node).items():
            if isinstance(value, list):
                for item in value:
                    if hasattr(item, 'type'):
                        yield from self._walk_js_ast(item)
            elif hasattr(value, 'type'):
                yield from self._walk_js_ast(value)

    def _find_function_end_esprima(self, lines: list[str], start_line_1b: int) -> int | None:
        if esprima is None:
            return None
        try:
            source = "\n".join(lines)
            tree = esprima.parseScript(source, {'loc': True, 'range': True})
            candidates = []
            for node in self._walk_js_ast(tree):
                if getattr(node, 'type', None) in (
                    'FunctionDeclaration', 'FunctionExpression', 'ArrowFunctionExpression', 'MethodDefinition'
                ) and hasattr(node, 'loc') and getattr(node.loc.start, 'line', 10**9) >= start_line_1b:
                    candidates.append(node)
            if not candidates:
                return None
            target = min(candidates, key=lambda n: n.loc.start.line)
            return int(target.loc.end.line)
        except Exception:
            return None

    def _find_js_function_end_braces(self, lines: list[str], start_line_1b: int) -> int:
        n = len(lines)
        i = max(0, start_line_1b - 1)
        # Find likely function starting brace
        while i < n:
            if any(k in lines[i] for k in ['function', '=>']):
                break
            i += 1
        if i >= n:
            return max(1, start_line_1b)
        brace_count = 0
        found_opening = False
        for j in range(i, n):
            for ch in lines[j]:
                if ch == '{':
                    brace_count += 1
                    found_opening = True
                elif ch == '}':
                    brace_count -= 1
                    if found_opening and brace_count == 0:
                        return j + 1
        return min(i + 10, n)

    def find_function_end(self, lines: list[str], start_line_1b: int) -> int:
        end_ast = self._find_function_end_esprima(lines, start_line_1b)
        if end_ast is not None:
            return end_ast
        return self._find_js_function_end_braces(lines, start_line_1b)


# Language registry
LANGUAGES: dict[str, LanguageConfig] = {
    'python': LanguageConfig(
        name='python',
        extensions={'.py'},
        function_parser=PythonFunctionParser()
    ),
    'javascript': LanguageConfig(
        name='javascript',
        extensions={'.js', '.jsx'},
        function_parser=JavaScriptFunctionParser()
    ),
    'typescript': LanguageConfig(
        name='typescript',
        extensions={'.ts', '.tsx'},
        function_parser=JavaScriptFunctionParser()
    ),
}


def get_language_for_file(file_path: Path) -> LanguageConfig | None:
    """Get language configuration for a file based on its extension."""
    ext = file_path.suffix.lower()
    for lang in LANGUAGES.values():
        if ext in lang.extensions:
            return lang
    return None


def get_supported_extensions() -> set[str]:
    """Get all supported file extensions."""
    extensions = set()
    for lang in LANGUAGES.values():
        extensions.update(lang.extensions)
    return extensions


def get_language_name_for_file(file_path: Path) -> str:
    """Get language name for syntax highlighting in markdown."""
    ext = file_path.suffix.lower()
    mapping = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
    }
    return mapping.get(ext, '')


def assemble_code_from_parts(parts: list[ExamplePart]) -> str:
    """Read and concatenate code lines for the given parts.

    Each part contributes the lines [code_start_line, code_end_line] (inclusive of start, exclusive of end as stored).
    Empty line is added between parts.
    """
    code_lines: list[str] = []
    for i, part in enumerate(parts):
        try:
            with open(part.file_path, encoding='utf-8') as f:
                file_lines = f.readlines()
            start_idx = max(0, part.code_start_line - 1)
            end_idx = min(len(file_lines), part.code_end_line)
            seg = [ln.rstrip('\r\n') for ln in file_lines[start_idx:end_idx]]
            code_lines.extend(seg)
            if i < len(parts) - 1:
                code_lines.append("")
        except Exception:
            # Skip unreadable parts silently
            continue
    return "\n".join(code_lines)
