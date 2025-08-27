"""Language-specific parsing and configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class LanguageConfig:
    """Configuration for a supported language."""
    name: str
    extensions: Set[str]
    function_parser: 'FunctionParser'


class FunctionParser(ABC):
    """Abstract base class for language-specific function boundary detection."""
    
    @abstractmethod
    def find_function_end(self, lines: List[str], start_line_1b: int) -> int:
        """Find the end line of a function starting at start_line_1b (1-based).
        
        Args:
            lines: File content as list of lines
            start_line_1b: Starting line number (1-based) right after @/unsafe marker
            
        Returns:
            End line number (1-based, inclusive) of the function
        """
        pass


class PythonFunctionParser(FunctionParser):
    """Parser for Python function boundaries."""
    
    def find_function_end(self, lines: List[str], start_line_1b: int) -> int:
        """Find the end of a Python function using indentation."""
        n = len(lines)
        i = max(0, start_line_1b - 1)

        # Skip blank lines and comments until we find decorators or function
        while i < n and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
            i += 1

        # Capture decorators
        deco_start = None
        while i < n and lines[i].lstrip().startswith("@"):
            deco_start = i if deco_start is None else deco_start
            i += 1

        # Find function definition
        def_line = i
        while def_line < n:
            stripped = lines[def_line].lstrip()
            if stripped.startswith("def ") or stripped.startswith("async def "):
                break
            # If we see unrelated top-level code, fallback
            if stripped and not lines[def_line].startswith(" "):
                break
            def_line += 1

        if def_line >= n:
            # Fallback: single line
            return max(1, start_line_1b)

        # Use decorator start if present, otherwise function start
        actual_start = deco_start if deco_start is not None else def_line
        
        # Find function end by tracking indentation
        base_indent = len(lines[def_line]) - len(lines[def_line].lstrip(" "))
        j = def_line + 1
        last_content = def_line
        
        while j < n:
            line = lines[j]
            stripped = line.lstrip()
            if not stripped:  # Empty line
                j += 1
                continue
                
            current_indent = len(line) - len(stripped)
            if current_indent <= base_indent:
                # We've left the function
                break
            last_content = j
            j += 1

        return last_content + 1  # Convert to 1-based


class JavaScriptFunctionParser(FunctionParser):
    """Parser for JavaScript/TypeScript function boundaries using braces."""
    
    def find_function_end(self, lines: List[str], start_line_1b: int) -> int:
        """Find the end of a JS/TS function using brace matching."""
        n = len(lines)
        i = max(0, start_line_1b - 1)
        
        # Find function declaration/expression
        while i < n:
            line = lines[i].strip()
            # Look for function keywords or arrow functions
            if any(keyword in line for keyword in ['function', '=>', 'function*']):
                break
            i += 1
            
        if i >= n:
            return max(1, start_line_1b)
            
        # Count braces to find function end
        brace_count = 0
        found_opening = False
        
        for j in range(i, n):
            line = lines[j]
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening = True
                elif char == '}':
                    brace_count -= 1
                    if found_opening and brace_count == 0:
                        return j + 1  # Found matching closing brace
        
        # If we didn't find proper braces, return a reasonable fallback
        return min(i + 10, n)  # Function likely within next 10 lines


# Language registry
LANGUAGES: Dict[str, LanguageConfig] = {
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


def get_supported_extensions() -> Set[str]:
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
