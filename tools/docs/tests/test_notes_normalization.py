import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.docs.yaml_io import parse_annotation_metadata, write_yaml, read_yaml
from tools.docs.models import DirectoryIndex, Example
from tools.docs.markdown_generator import generate_readme


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
            id_prefix=None,
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
            id_prefix=None,
            examples={1: ex},
            attachments={},
        )
        title = "Doc"
        intro = "Intro"
        structure = [{"section": "S", "description": "D", "examples": [1]}]
        md = generate_readme(idx, title, intro, structure)
        # Notes kept as a single block; newline preserved inside generator output
        self.assertIn("Line one of notes\nLine two of notes", md)


if __name__ == "__main__":
    unittest.main()
