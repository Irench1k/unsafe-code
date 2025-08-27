"""Tests for language support."""

import unittest
from pathlib import Path

from ..languages import (
    get_language_for_file,
    get_supported_extensions, 
    PythonFunctionParser,
    JavaScriptFunctionParser,
)


class TestLanguages(unittest.TestCase):
    
    def test_get_language_for_file(self):
        """Test language detection by file extension."""
        # Python
        lang = get_language_for_file(Path("test.py"))
        self.assertIsNotNone(lang)
        self.assertEqual(lang.name, "python")
        
        # JavaScript
        lang = get_language_for_file(Path("test.js"))
        self.assertIsNotNone(lang)
        self.assertEqual(lang.name, "javascript")
        
        # TypeScript
        lang = get_language_for_file(Path("test.ts"))
        self.assertIsNotNone(lang)
        self.assertEqual(lang.name, "typescript")
        
        # Unsupported
        lang = get_language_for_file(Path("test.txt"))
        self.assertIsNone(lang)
    
    def test_get_supported_extensions(self):
        """Test getting supported extensions."""
        extensions = get_supported_extensions()
        expected = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        self.assertEqual(extensions, expected)


class TestPythonFunctionParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = PythonFunctionParser()
    
    def test_simple_function(self):
        """Test parsing a simple function."""
        lines = [
            "",  # line 1
            "def test_function():",  # line 2
            "    return 42",  # line 3
            "",  # line 4
            "def another_function():",  # line 5
        ]
        
        # Starting at line 2 (1-based)
        end_line = self.parser.find_function_end(lines, 2)
        self.assertEqual(end_line, 3)  # Should end at line 3
    
    def test_function_with_decorator(self):
        """Test function with decorators."""
        lines = [
            "",  # line 1
            "@decorator",  # line 2
            "@another_decorator",  # line 3 
            "def test_function():",  # line 4
            "    pass",  # line 5
            "",  # line 6
            "def next_function():",  # line 7
        ]
        
        # Starting at line 2 (where @unsafe marker would be)
        end_line = self.parser.find_function_end(lines, 2)
        self.assertEqual(end_line, 5)  # Should include the function body
    
    def test_async_function(self):
        """Test async function parsing."""
        lines = [
            "",
            "async def async_function():",
            "    await something()",
            "    return result",
            "",
            "def next_function():",
        ]
        
        end_line = self.parser.find_function_end(lines, 2)
        self.assertEqual(end_line, 4)
    
    def test_nested_function(self):
        """Test function with nested blocks."""
        lines = [
            "",
            "def complex_function():",
            "    if True:",
            "        for i in range(10):",
            "            print(i)",
            "    return 'done'",
            "",
            "def next_function():",
        ]
        
        end_line = self.parser.find_function_end(lines, 2)
        self.assertEqual(end_line, 6)


class TestJavaScriptFunctionParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = JavaScriptFunctionParser()
    
    def test_function_declaration(self):
        """Test parsing function declaration."""
        lines = [
            "",
            "function testFunction() {",
            "    return 42;",
            "}",
            "",
            "function anotherFunction() {",
        ]
        
        end_line = self.parser.find_function_end(lines, 2)
        self.assertEqual(end_line, 4)
    
    def test_arrow_function(self):
        """Test parsing arrow function."""
        lines = [
            "",
            "const testFunc = () => {",
            "    console.log('test');",
            "    return true;",
            "};",
            "",
        ]
        
        end_line = self.parser.find_function_end(lines, 2)
        self.assertEqual(end_line, 5)
    
    def test_nested_braces(self):
        """Test function with nested braces."""
        lines = [
            "",
            "function complex() {",
            "    if (true) {",
            "        for (let i = 0; i < 10; i++) {",
            "            console.log(i);",
            "        }",
            "    }",
            "    return 'done';",
            "}",
            "",
        ]
        
        end_line = self.parser.find_function_end(lines, 2)
        self.assertEqual(end_line, 9)


if __name__ == '__main__':
    unittest.main()
