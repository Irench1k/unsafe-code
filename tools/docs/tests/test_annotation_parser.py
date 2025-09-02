"""Tests for annotation parser."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.docs.annotation_parser import (
    find_annotation_boundaries,
    find_closing_marker,
    extract_yaml_content,
    remove_comment_prefix,
    parse_annotation_metadata,
    parse_file_annotations,
)


class TestAnnotationParser(unittest.TestCase):
    
    def test_find_annotation_boundaries(self):
        result = find_annotation_boundaries("# @unsafe[function]")
        self.assertEqual(result, ("function", 0))

        result = find_annotation_boundaries("    # @unsafe[block]")
        self.assertEqual(result, ("block", 4))

        result = find_annotation_boundaries("// @unsafe[function]")
        self.assertEqual(result, ("function", 0))

        result = find_annotation_boundaries("# This is just a comment")
        self.assertIsNone(result)
    
    def test_find_closing_marker(self):
        lines = [
            "# @unsafe[function]",
            "# id: 1",
            "# @/unsafe",
            "def test():",
            "    pass"
        ]
        result = find_closing_marker(lines, 0, 0)
        self.assertEqual(result, 2)

        lines_no_close = [
            "# @unsafe[function]",
            "# id: 1",
        ]
        result = find_closing_marker(lines_no_close, 0, 0)
        self.assertIsNone(result)
    
    def test_extract_yaml_content(self):
        lines = [
            "# @unsafe[function]",
            "# id: 1",
            "# title: Test Function",
            "# @/unsafe",
        ]
        result = extract_yaml_content(lines, 0, 3)
        expected = "id: 1\ntitle: Test Function"
        self.assertEqual(result, expected)
    
    def test_remove_comment_prefix(self):
        result = remove_comment_prefix("# content here")
        self.assertEqual(result, " content here")

        result = remove_comment_prefix("// content here")
        self.assertEqual(result, " content here")

        result = remove_comment_prefix("    # content here")
        self.assertEqual(result, "     content here")

        result = remove_comment_prefix("just text")
        self.assertEqual(result, "just text")
    
    def test_parse_annotation_metadata(self):
        yaml_content = """
id: 1
title: Test Example
notes: |
  This is a test note
  with multiple lines
http: open
"""
        result = parse_annotation_metadata(yaml_content)
        expected = {
            'id': 1,
            'title': 'Test Example',
            'notes': 'This is a test note with multiple lines',
            'http': 'open'
        }
        self.assertEqual(result, expected)

        invalid_yaml = "title: Test"
        with self.assertRaises(ValueError):
            parse_annotation_metadata(invalid_yaml)
    
    def test_parse_file_annotations(self):
        content = """# Example Python file
# @unsafe[function]
# id: 1
# title: Test Function
# @/unsafe
def test_function():
    \"\"\"A test function.\"\"\"
    return \"hello\"

# @unsafe[block] 
# id: 2
# title: Test Block
# part: 1
# @/unsafe
x = 1
y = 2
# @/unsafe[block]

def another_function():
    pass
"""
        with TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test.py"
            test_file.write_text(content)
            annotations = parse_file_annotations(test_file)
            self.assertEqual(len(annotations), 2)

            func_ann = annotations[0]
            self.assertEqual(func_ann.kind, "function")
            self.assertEqual(func_ann.metadata['id'], 1)
            self.assertEqual(func_ann.metadata['title'], "Test Function")

            block_ann = annotations[1]
            self.assertEqual(block_ann.kind, "block")
            self.assertEqual(block_ann.metadata['id'], 2)
            self.assertEqual(block_ann.metadata['title'], "Test Block")
            self.assertEqual(block_ann.metadata['part'], 1)


if __name__ == '__main__':
    unittest.main()
