#!/usr/bin/env python3
"""
Unsafe Code Lab - Focus Script
Dynamically sets VSCode files.exclude to focus on a specific directory.

Usage:
    uv run focus vulnerabilities/python/flask/confusion/webapp/r02_authentication_confusion/e03_fake_header_refund
    uv run focus reset  # Clear all focus filters
    uv run focus status # Show current focus
"""

import json
import sys
from pathlib import Path

MANAGED_EXCLUDES_KEY = "_focus_managed_excludes"
PREV_EXCLUDE_GITIGNORE_KEY = "_focus_prev_exclude_gitignore"

REPO_ROOT = Path(__file__).resolve().parent.parent
VSCODE_DIR = REPO_ROOT / ".vscode"
SETTINGS_FILE = VSCODE_DIR / "settings.json"


def load_settings():
    """Load existing VSCode settings or create empty dict."""
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    return {}


def save_settings(settings):
    """Save settings to VSCode settings.json."""
    VSCODE_DIR.mkdir(exist_ok=True)
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)
        f.write('\n')


def get_focus_excludes(focus_path):
    """
    Generate files.exclude patterns to hide everything except focus_path.

    Strategy:
    - Hide all examples in the same round except the focused one
    - Hide all rounds except the focused round
    - Keep showing non-example files (README, compose files, etc.)
    """
    # Ensure focus_path is a Path object and already relative
    focus = Path(focus_path) if not isinstance(focus_path, Path) else focus_path
    excludes = {}

    # Parse the focus path to understand what to hide
    parts = focus.parts

    if 'webapp' in parts:
        webapp_idx = parts.index('webapp')

        # If focusing on a specific round (r01, r02, etc.)
        if webapp_idx + 1 < len(parts):
            round_dir = parts[webapp_idx + 1]

            # Hide all other rounds
            if round_dir.startswith('r'):
                webapp_path = Path(*parts[:webapp_idx+1])
                for other_round in (REPO_ROOT / webapp_path).glob('r*'):
                    if other_round.name != round_dir:
                        rel_path = other_round.relative_to(REPO_ROOT)
                        excludes[f"{rel_path}"] = True

                # If focusing on a specific example (e01, e02, etc.)
                if webapp_idx + 2 < len(parts):
                    example_dir = parts[webapp_idx + 2]
                    if example_dir.startswith('e'):
                        round_path = Path(*parts[:webapp_idx+2])
                        for other_example in (REPO_ROOT / round_path).glob('e*'):
                            if other_example.name != example_dir:
                                rel_path = other_example.relative_to(REPO_ROOT)
                                excludes[f"{rel_path}"] = True

    return excludes


def get_root_dotfile_excludes():
    """Hide dotfiles that live in the repo root to keep focus uncluttered."""
    excludes = {}
    for entry in REPO_ROOT.iterdir():
        if entry.name.startswith('.') and entry.name not in {'.', '..'}:
            excludes[entry.name] = True
    return excludes


def get_vulnerability_focus_excludes(focus_path):
    """Hide other languages/frameworks inside vulnerabilities when focusing."""
    excludes = {}
    parts = focus_path.parts

    if len(parts) >= 2 and parts[0] == 'vulnerabilities':
        language = parts[1]
        vulnerabilities_root = REPO_ROOT / 'vulnerabilities'
        if vulnerabilities_root.exists():
            for candidate in vulnerabilities_root.iterdir():
                if candidate.is_dir() and candidate.name != language:
                    rel = Path('vulnerabilities') / candidate.name
                    excludes[str(rel)] = True

        if len(parts) >= 3:
            framework = parts[2]
            language_root = vulnerabilities_root / language
            if language_root.exists():
                for candidate in language_root.iterdir():
                    if candidate.is_dir() and candidate.name != framework:
                        rel = Path('vulnerabilities') / language / candidate.name
                        excludes[str(rel)] = True

    return excludes


def enable_gitignore_exclusion(settings):
    """Ensure VSCode hides anything covered by .gitignore while focused."""
    if PREV_EXCLUDE_GITIGNORE_KEY not in settings:
        settings[PREV_EXCLUDE_GITIGNORE_KEY] = settings.get('explorer.excludeGitIgnore')
    settings['explorer.excludeGitIgnore'] = True


def focus_on(path_arg):
    """Set focus on a specific directory."""
    # Convert to Path and handle absolute vs relative
    if Path(path_arg).is_absolute():
        full_path = Path(path_arg)
        try:
            focus_path = full_path.relative_to(REPO_ROOT)
        except ValueError:
            print(f"❌ Path must be within repository: {REPO_ROOT}")
            sys.exit(1)
    else:
        focus_path = Path(path_arg)
        full_path = REPO_ROOT / focus_path

    # Verify path exists
    if not full_path.exists():
        print(f"❌ Path does not exist: {full_path}")
        sys.exit(1)

    settings = load_settings()

    excludes = settings.setdefault("files.exclude", {})
    managed = settings.get(MANAGED_EXCLUDES_KEY, [])
    for key in managed:
        excludes.pop(key, None)

    focus_excludes = {}
    focus_excludes.update(get_root_dotfile_excludes())
    focus_excludes.update(get_vulnerability_focus_excludes(focus_path))
    focus_excludes.update(get_focus_excludes(focus_path))

    excludes.update(focus_excludes)
    settings[MANAGED_EXCLUDES_KEY] = sorted(focus_excludes.keys())

    # Add marker comment (in a way that VSCode will preserve)
    settings["_focus_script_marker"] = f"Focused on: {focus_path}"

    enable_gitignore_exclusion(settings)

    save_settings(settings)

    print(f"✅ Focused on: {focus_path}")
    print(f"📂 Hiding {len(focus_excludes)} directories")
    for excluded in sorted(focus_excludes.keys())[:5]:
        print(f"   - {excluded}")
    if len(focus_excludes) > 5:
        print(f"   ... and {len(focus_excludes) - 5} more")


def reset_focus():
    """Remove all focus filters."""
    settings = load_settings()

    if "files.exclude" in settings:
        excludes = settings["files.exclude"]
        for key in settings.get(MANAGED_EXCLUDES_KEY, []):
            excludes.pop(key, None)
        if not excludes:
            del settings["files.exclude"]

    settings.pop(MANAGED_EXCLUDES_KEY, None)

    if "_focus_script_marker" in settings:
        del settings["_focus_script_marker"]

    if PREV_EXCLUDE_GITIGNORE_KEY in settings:
        previous = settings.pop(PREV_EXCLUDE_GITIGNORE_KEY)
        if previous is None:
            settings.pop('explorer.excludeGitIgnore', None)
        else:
            settings['explorer.excludeGitIgnore'] = previous

    save_settings(settings)
    print("✅ Focus reset - all directories visible")


def show_status():
    """Show current focus status."""
    settings = load_settings()

    if "_focus_script_marker" in settings:
        print(f"🎯 Currently focused: {settings['_focus_script_marker']}")
        managed = settings.get(MANAGED_EXCLUDES_KEY, [])
        print(f"📂 Hiding {len(managed)} directories")
    else:
        print("ℹ️  No focus set (all directories visible)")


def main(argv: list[str] | None = None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(__doc__)
        sys.exit(1)

    command = args[0]

    if command == "reset":
        reset_focus()
    elif command == "status":
        show_status()
    elif command in ["-h", "--help", "help"]:
        print(__doc__)
    else:
        focus_on(command)


if __name__ == "__main__":
    main()
