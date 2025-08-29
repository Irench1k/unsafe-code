import unittest
from pathlib import Path

from tools.docs.readme_spec import load_readme_spec
from tools.docs.markdown_generator import generate_readme
from tools.docs.models import DirectoryIndex, Example


class TestSpecNormalization(unittest.TestCase):
    def test_intro_and_description_normalization(self):
        # Prepare a synthetic spec as dict written to a temp file
        from tempfile import TemporaryDirectory
        import yaml

        spec_data = {
            "title": "Doc",
            "intro": "Line A\nLine B\n\n```http\nGET /x\n```\n\nLine C",
            "structure": [
                {
                    "section": "S",
                    "description": "Desc line 1\nDesc line 2\n\nDesc para 2",
                    "examples": [1],
                }
            ],
        }
        with TemporaryDirectory() as td:
            p = Path(td) / "readme.yml"
            p.write_text(yaml.safe_dump(spec_data), encoding="utf-8")
            spec = load_readme_spec(p)
            idx = DirectoryIndex(
                version="1",
                root=Path("."),
                category=None,
                id_prefix=None,
                examples={1: Example(id=1, kind="function", title="T", notes=None, parts=[])},
                attachments={},
            )
            md = generate_readme(idx, spec.title, spec.intro, [{
                "section": spec.sections[0].title,
                "description": spec.sections[0].description,
                "examples": [1]
            }])

            # Intro collapses intra-paragraph newlines, preserves code block and blank lines
            self.assertIn("Line A Line B\n\n```http\nGET /x\n```\n\nLine C", spec.intro)
            # Description single paragraph collapse
            self.assertIn("Desc line 1 Desc line 2", spec.sections[0].description)
            # README contains normalized description
            self.assertIn("Desc line 1 Desc line 2", md)


if __name__ == "__main__":
    unittest.main()

