"""Tests for language support."""

import unittest
from pathlib import Path

from tools.docs.languages import (
    get_language_for_file,
    get_supported_extensions, 
    PythonFunctionParser,
    JavaScriptFunctionParser,
)


class TestLanguages(unittest.TestCase):
    
    def test_get_language_for_file(self):
        lang = get_language_for_file(Path("test.py"))
        self.assertIsNotNone(lang)
        self.assertEqual(lang.name, "python")

        lang = get_language_for_file(Path("test.js"))
        self.assertIsNotNone(lang)
        self.assertEqual(lang.name, "javascript")

        lang = get_language_for_file(Path("test.ts"))
        self.assertIsNotNone(lang)
        self.assertEqual(lang.name, "typescript")

        lang = get_language_for_file(Path("test.txt"))
        self.assertIsNone(lang)
    
    def test_get_supported_extensions(self):
        extensions = get_supported_extensions()
        expected = {'.py', '.js', '.jsx', '.ts', '.tsx'}
        self.assertEqual(extensions, expected)


class TestPythonFunctionParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = PythonFunctionParser()
    
    def test_simple_function(self):
        lines = [
            "",
            "def test_function():",
            "    return 42",
            "",
            "def another_function():",
        ]
        end_line = self.parser.find_function_end(lines, 2)
        self.assertEqual(end_line, 3)
    
    def test_function_with_decorator(self):
        lines = [
            "",
            "@decorator",
            "@another_decorator",
            "def test_function():",
            "    pass",
            "",
            "def next_function():",
        ]
        end_line = self.parser.find_function_end(lines, 2)
        self.assertEqual(end_line, 5)
    
    def test_async_function(self):
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

