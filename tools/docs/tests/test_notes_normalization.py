import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.docs.markdown_generator import generate_readme
from tools.docs.models import DirectoryIndex, Example
from tools.docs.yaml_io import parse_annotation_metadata, write_yaml


class TestNotesNormalization(unittest.TestCase):
    def test_normalize_single_paragraph_and_blank_lines(self):
        yaml_content = """
id: 1
notes: |
  This is a test note
  with multiple lines

  And a new paragraph.
"""
        data = parse_annotation_metadata(yaml_content)
        # Expect single paragraph lines joined by a space, blank lines collapsed
        self.assertEqual(
            data["notes"],
            "This is a test note with multiple lines\n\nAnd a new paragraph.",
        )

    def test_preserve_fenced_code_blocks(self):
        yaml_content = """
id: 2
notes: |
  Paragraph before code.

  ```http
  GET /test
  ```

  Paragraph after code.
"""
        data = parse_annotation_metadata(yaml_content)
        expected = (
            "Paragraph before code.\n\n" "```http\nGET /test\n```\n\n" "Paragraph after code."
        )
        self.assertEqual(data["notes"], expected)

    def test_yaml_dump_uses_folded_style_for_notes(self):
        # Build minimal index dict with normalized notes
        ex = Example(id=1, kind="function", title="T", notes="A note with many words " * 6)
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={1: ex},
            attachments={},
        )
        with TemporaryDirectory() as td:
            out = Path(td) / "index.yml"
            write_yaml(out, idx.to_dict())
            text = out.read_text(encoding="utf-8")
            # Ensure 'notes:' block exists and does not contain excessive empty lines
            self.assertIn("notes:", text)
            # No triple consecutive empty lines
            self.assertNotIn("\n\n\n", text)

    def test_readme_render_contains_normalized_notes(self):
        # Ensure README contains the normalized paragraph text (no mid-line breaks)
        ex = Example(
            id=1,
            kind="function",
            title="T",
            notes="Line one of notes\nLine two of notes",
        )
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={1: ex},
            attachments={},
        )
        title = "Doc"
        summary = ""
        description = "Intro"
        structure = [{"title": "S", "description": "D", "examples": [1]}]
        md = generate_readme(idx, title, summary, description, structure, toc=False)
        # Notes kept as a single block; newline preserved inside generator output
        self.assertIn("Line one of notes\nLine two of notes", md)

    def test_preserve_unordered_list_with_dashes(self):
        """Test that unordered lists with dashes are preserved."""
        yaml_content = """
id: 3
notes: |
  Practice tips:

  - Set `Vary` headers intentionally and confirm your CDN respects them.
  - Avoid caching authenticated endpoints at the edge unless you can key by user or tenant.
  - Document which headers your cache strips or normalizes before they hit Flask.
"""
        data = parse_annotation_metadata(yaml_content)
        # Lists should be preserved with newlines between items
        expected = (
            "Practice tips:\n\n"
            "- Set `Vary` headers intentionally and confirm your CDN respects them.\n"
            "- Avoid caching authenticated endpoints at the edge unless you can key by user or tenant.\n"
            "- Document which headers your cache strips or normalizes before they hit Flask."
        )
        self.assertEqual(data["notes"], expected)

    def test_preserve_unordered_list_with_asterisks(self):
        """Test that unordered lists with asterisks are preserved."""
        yaml_content = """
id: 4
notes: |
  Key points:

  * First important point
  * Second important point
  * Third important point
"""
        data = parse_annotation_metadata(yaml_content)
        expected = (
            "Key points:\n\n"
            "* First important point\n"
            "* Second important point\n"
            "* Third important point"
        )
        self.assertEqual(data["notes"], expected)

    def test_preserve_ordered_list(self):
        """Test that ordered lists are preserved."""
        yaml_content = """
id: 5
notes: |
  Steps to reproduce:

  1. First step here
  2. Second step here
  3. Third step here
"""
        data = parse_annotation_metadata(yaml_content)
        expected = (
            "Steps to reproduce:\n\n"
            "1. First step here\n"
            "2. Second step here\n"
            "3. Third step here"
        )
        self.assertEqual(data["notes"], expected)

    def test_preserve_mixed_content_with_lists(self):
        """Test that paragraphs and lists are both handled correctly."""
        yaml_content = """
id: 6
notes: |
  This is an introductory paragraph
  that spans multiple lines.

  Here are some points:

  - First bullet point
  - Second bullet point

  And a concluding paragraph
  that also spans lines.
"""
        data = parse_annotation_metadata(yaml_content)
        expected = (
            "This is an introductory paragraph that spans multiple lines.\n\n"
            "Here are some points:\n\n"
            "- First bullet point\n"
            "- Second bullet point\n\n"
            "And a concluding paragraph that also spans lines."
        )
        self.assertEqual(data["notes"], expected)

    def test_readme_description_preserves_lists(self):
        """Test that lists in readme description field are preserved in generated markdown."""
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={},
            attachments={},
        )
        title = "Test Doc"
        summary = "A brief summary"
        description = (
            "**Practice tips:**\n\n"
            "- Set `Vary` headers intentionally and confirm your CDN respects them.\n"
            "- Avoid caching authenticated endpoints at the edge unless you can key by user or tenant.\n"
            "- Document which headers your cache strips or normalizes before they hit Flask."
        )
        structure = []
        md = generate_readme(idx, title, summary, description, structure, toc=False)

        # Each list item should be on its own line
        self.assertIn("- Set `Vary` headers intentionally", md)
        self.assertIn("\n- Avoid caching authenticated endpoints", md)
        self.assertIn("\n- Document which headers your cache strips", md)

        # They should NOT be collapsed into a single line
        self.assertNotIn("- Set `Vary` headers intentionally and confirm your CDN respects them. - Avoid caching", md)

    def test_readme_spacing_title_and_summary(self):
        """Test that there's a blank line between title and summary."""
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={},
            attachments={},
        )
        title = "Test Title"
        summary = "This is a summary line."
        description = ""
        structure = []
        md = generate_readme(idx, title, summary, description, structure, toc=False)

        # Should have blank line between title and summary
        self.assertIn("# Test Title\n\nThis is a summary line.", md)
        # Should NOT be directly adjacent
        self.assertNotIn("# Test Title\nThis is a summary line.", md)

    def test_readme_spacing_summary_and_description(self):
        """Test that there's a blank line between summary and description."""
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={},
            attachments={},
        )
        title = "Test Title"
        summary = "This is a summary line."
        description = "## Overview\n\nThis is the description section."
        structure = []
        md = generate_readme(idx, title, summary, description, structure, toc=False)

        # Should have blank line between summary and description header
        self.assertIn("This is a summary line.\n\n## Overview", md)
        # Should NOT be directly adjacent
        self.assertNotIn("This is a summary line.\n## Overview", md)

    def test_readme_spacing_title_and_description_no_summary(self):
        """Test that there's a blank line between title and description when no summary."""
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={},
            attachments={},
        )
        title = "Test Title"
        summary = ""
        description = "## Overview\n\nThis is the description section."
        structure = []
        md = generate_readme(idx, title, summary, description, structure, toc=False)

        # Should have blank line between title and description
        self.assertIn("# Test Title\n\n## Overview", md)
        # Should NOT be directly adjacent
        self.assertNotIn("# Test Title\n## Overview", md)

    def test_readme_spacing_all_sections(self):
        """Test proper spacing when all sections (title, summary, description) are present."""
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={},
            attachments={},
        )
        title = "Full Document"
        summary = "A short summary."
        description = "## Introduction\n\nDetailed description here."
        structure = []
        md = generate_readme(idx, title, summary, description, structure, toc=False)

        # All sections should have proper spacing
        expected = "# Full Document\n\nA short summary.\n\n## Introduction\n\nDetailed description here."
        self.assertIn(expected, md)

    def test_readme_spacing_section_headers(self):
        """Test that section headers (H2) have blank lines after them."""
        ex = Example(id=1, kind="function", title="Test Example", notes="Example notes")
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={1: ex},
            attachments={},
        )
        title = "Doc"
        summary = ""
        description = ""
        structure = [{"title": "Section Title", "description": "Section description.", "examples": [1]}]
        md = generate_readme(idx, title, summary, description, structure, toc=False)

        # Section header should have blank line after it
        self.assertIn("## Section Title\n\nSection description.", md)
        # Should NOT be directly adjacent
        self.assertNotIn("## Section Title\nSection description.", md)

    def test_readme_spacing_section_description_and_examples(self):
        """Test that there's blank line between section description and example header."""
        ex = Example(id=1, kind="function", title="Test Example", notes="Example notes")
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={1: ex},
            attachments={},
        )
        title = "Doc"
        summary = ""
        description = ""
        structure = [{"title": "Section Title", "description": "Section description.", "examples": [1]}]
        md = generate_readme(idx, title, summary, description, structure, toc=False)

        # Should have blank line between description and example header (with inline anchor)
        self.assertIn("Section description.\n\n### Example 1: Test Example <a id=\"ex-1\"></a>", md)
        # Should NOT be directly adjacent
        self.assertNotIn("Section description.\n### Example 1: Test Example", md)

    def test_readme_inline_anchor_in_header(self):
        """Test that anchor tag is inline with the example header."""
        ex = Example(id=1, kind="function", title="Test Example", notes="Example notes")
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={1: ex},
            attachments={},
        )
        title = "Doc"
        summary = ""
        description = ""
        structure = [{"title": "", "description": "", "examples": [1]}]
        md = generate_readme(idx, title, summary, description, structure, toc=False)

        # Anchor should be inline with header
        self.assertIn("### Example 1: Test Example <a id=\"ex-1\"></a>", md)
        # Should NOT be on separate lines
        self.assertNotIn("<a id=\"ex-1\"></a>\n### Example 1: Test Example", md)

    def test_readme_spacing_example_header_and_notes(self):
        """Test that there's a blank line between example header (with inline anchor) and notes."""
        ex = Example(id=1, kind="function", title="Test Example", notes="Example notes")
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={1: ex},
            attachments={},
        )
        title = "Doc"
        summary = ""
        description = ""
        structure = [{"title": "", "description": "", "examples": [1]}]
        md = generate_readme(idx, title, summary, description, structure, toc=False)

        # Should have blank line between header (with anchor) and notes
        self.assertIn("### Example 1: Test Example <a id=\"ex-1\"></a>\n\nExample notes", md)
        # Should NOT be directly adjacent
        self.assertNotIn("<a id=\"ex-1\"></a>\nExample notes", md)

    def test_readme_spacing_multiple_sections_and_examples(self):
        """Test proper spacing with multiple sections and examples."""
        ex1 = Example(id=1, kind="function", title="First", notes="First notes")
        ex2 = Example(id=2, kind="function", title="Second", notes="Second notes")
        idx = DirectoryIndex(
            version="1",
            root=Path("."),
            category=None,
            namespace=None,
            examples={1: ex1, 2: ex2},
            attachments={},
        )
        title = "Doc"
        summary = "Summary"
        description = ""
        structure = [
            {"title": "Section A", "description": "Desc A", "examples": [1]},
            {"title": "Section B", "description": "Desc B", "examples": [2]},
        ]
        md = generate_readme(idx, title, summary, description, structure, toc=False)

        # Check spacing for first section (anchor is now inline)
        self.assertIn("## Section A\n\nDesc A\n\n### Example 1: First <a id=\"ex-1\"></a>", md)
        self.assertIn("### Example 1: First <a id=\"ex-1\"></a>\n\nFirst notes", md)

        # Check spacing for second section
        self.assertIn("## Section B\n\nDesc B\n\n### Example 2: Second <a id=\"ex-2\"></a>", md)
        self.assertIn("### Example 2: Second <a id=\"ex-2\"></a>\n\nSecond notes", md)


if __name__ == "__main__":
    unittest.main()
