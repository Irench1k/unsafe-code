"""Link checker for markdown files."""

import os
import re
from pathlib import Path


def extract_markdown_links(content: str) -> list[tuple[str, str]]:
    """Extract all markdown links from content.

    Returns list of (link_text, url) tuples.
    """
    # Match [text](url) or [text](url#anchor)
    pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    matches = re.findall(pattern, content)
    return [(text, url) for text, url in matches]


def is_external_link(url: str) -> bool:
    """Check if a URL is external (http/https)."""
    return url.startswith(('http://', 'https://'))


def is_anchor_only(url: str) -> bool:
    """Check if URL is just an anchor (#something)."""
    return url.startswith('#')


def resolve_link(readme_path: Path, link_url: str) -> Path | None:
    """Resolve a relative link from a README file.

    Returns None if the link is an anchor-only link.
    """
    # Remove anchor if present
    url_without_anchor = link_url.split('#')[0]
    if not url_without_anchor:
        # Just an anchor, these are harder to validate
        return None

    readme_dir = readme_path.parent
    resolved = readme_dir / url_without_anchor
    return resolved.resolve()


class BrokenLink:
    """Represents a broken link in a markdown file."""

    def __init__(
        self,
        readme_path: Path,
        link_text: str,
        link_url: str,
        resolved_path: Path,
    ):
        self.readme_path = readme_path
        self.link_text = link_text
        self.link_url = link_url
        self.resolved_path = resolved_path

    def relative_readme(self, repo_root: Path) -> str:
        """Get the relative path of the README from repo root."""
        try:
            return str(self.readme_path.relative_to(repo_root))
        except ValueError:
            return str(self.readme_path)


def check_readme_links(readme_path: Path) -> list[BrokenLink]:
    """Check all links in a README file.

    Returns list of broken links found.
    """
    broken_links = []

    with open(readme_path, encoding='utf-8') as f:
        content = f.read()

    links = extract_markdown_links(content)

    for text, url in links:
        # Skip external links
        if is_external_link(url):
            continue

        # Skip anchor-only links
        if is_anchor_only(url):
            continue

        # Resolve relative link
        resolved_path = resolve_link(readme_path, url)
        if resolved_path is None:
            continue

        # Check if file/directory exists
        if not resolved_path.exists():
            broken_links.append(
                BrokenLink(
                    readme_path=readme_path,
                    link_text=text,
                    link_url=url,
                    resolved_path=resolved_path,
                )
            )

    return broken_links


def find_all_readme_files(repo_root: Path) -> list[Path]:
    """Find all README.md files in the repository.

    Excludes hidden directories and common exclusions.
    """
    readme_files = []
    for root, dirs, files in os.walk(repo_root):
        # Skip hidden directories and common exclusions
        dirs[:] = [
            d for d in dirs
            if not d.startswith('.')
            and d not in ['node_modules', '__pycache__', 'venv', '.venv']
        ]
        if 'README.md' in files:
            readme_files.append(Path(root) / 'README.md')
    return sorted(readme_files)


def check_all_links(repo_root: Path) -> list[BrokenLink]:
    """Check all links in all README files.

    Returns list of all broken links found.
    """
    readme_files = find_all_readme_files(repo_root)
    all_broken = []

    for readme_path in readme_files:
        broken = check_readme_links(readme_path)
        all_broken.extend(broken)

    return all_broken
