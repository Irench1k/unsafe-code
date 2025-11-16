# Unsafe Code Lab - Development Helpers

This directory contains tools to improve the developer experience when working on Unsafe Code Lab's multi-language, multi-framework monorepo.

## The Problem

When working on Flask confusion tutorials (or any tutorial with multiple similar examples):
- **File Confusion**: VSCode autocomplete suggests files from other examples (e.g., `r01/e01/auth.py` when you want `r02/e03/auth.py`)
- **Navigation Pain**: Constantly typing `cd` to move between nested directories
- **Docker Compose Context**: Need to run `docker compose` from specific directories while working in nested subdirectories

## The Solution

Two complementary tools:

### 1. Focus Script (`uv run focus`)

**Purpose**: Dynamically hide directories in VSCode to focus on a specific example.

**How it works**: Modifies `.vscode/settings.json` to use VSCode's `files.exclude` feature. When you focus on `r02/e03`, it hides:
- All other rounds (r01, r03, r04, etc.)
- All other examples in r02 (e01, e02, e04, etc.)

**Usage**:

```bash
# Focus on a specific example (full path)
uv run focus vulnerabilities/python/flask/confusion/webapp/r02_authentication_confusion/e03_fake_header_refund

# Reset focus (show all files)
uv run focus reset

# Check current focus
uv run focus status
```

**Result**:
- ✅ File search only finds files in focused example
- ✅ Autocomplete suggests correct files
- ✅ File tree is uncluttered
- ✅ Git/terminal still see all files (only VSCode UI is filtered)

### 2. Shell Helpers (`tools/dev/unsafe-code-dev.sh`)

**Purpose**: Streamline navigation and docker-compose workflows.

**Setup** (one-time):

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
source /path/to/unsafe-code/tools/dev/unsafe-code-dev.sh
```

Then restart your shell or run: `source ~/.zshrc`

**Usage**:

```bash
# Combined focus + navigation
ucfocus r02/e03              # Short form! Focuses VSCode AND navigates there
ucfocus r02/e03/routes       # Can focus on subdirectories too
ucunfocus                    # Clear focus

# Docker compose (works from anywhere)
ucup                         # Auto-finds compose.yml up the tree and runs docker compose up --build
ucdown                       # Stops containers
uclogs                       # Tails logs

# Quick navigation
uc                           # Jump to repo root
ucflask                      # Jump to Flask confusion directory
ucwebapp                     # Jump to webapp directory
ucgo r02/e03                 # Jump to specific round/example
uclist                       # List all examples in current round

# Help
uchelp                       # Show all commands
```

## Recommended Workflow

### Starting Work on an Example

```bash
# 1. Focus on the example you're working on
ucfocus r02/e03
# → This focuses VSCode file tree AND navigates you to that directory

# 2. Start docker compose (from anywhere)
ucup
# → Auto-finds compose.yml and runs from correct directory

# 3. Work on your code
# → VSCode only shows files from r02/e03
# → Autocomplete is accurate
# → No file confusion

# 4. When done
ucdown                       # Stop containers
ucunfocus                    # Clear focus (optional - or keep it focused)
```

### Switching Between Examples

```bash
# Switch to different example
ucfocus r02/e04              # Refocuses VSCode + navigates
ucup                         # Restart docker (if needed)
```

### Working on Multiple Examples

```bash
# Use VSCode's split editor or separate windows
# In terminal 1:
ucfocus r02/e03
ucup

# In terminal 2:
ucfocus r02/e04
ucup
# (Uses different ports via PORT env var if configured)
```

## Advanced Tips

### 1. Short Forms

The `ucfocus` and `ucgo` commands support short forms:

```bash
ucfocus r02/e03              # Instead of full path
ucgo r01/e02                 # Quick jump
```

### 2. Focus Granularity

You can focus at different levels:

```bash
ucfocus r02                  # Focus entire round (hides other rounds)
ucfocus r02/e03              # Focus specific example
ucfocus r02/e03/routes       # Focus subdirectory (not recommended - too narrow)
```

### 3. No More `cd` Pain

All docker commands work from anywhere:

```bash
# You're deep in code
cd vulnerabilities/python/flask/confusion/webapp/r02_authentication_confusion/e03_fake_header_refund/routes

# Need to restart containers?
ucdown && ucup               # Works! No need to cd up
```

### 4. VSCode Integration

The focus script works seamlessly with:
- ✅ File search (Cmd+P)
- ✅ Find in files (Cmd+Shift+F)
- ✅ Sidebar file tree
- ✅ Git integration (still sees all files)
- ✅ Terminal (still has access to all files)

## Comparison to Other Solutions

### Why Not Monorepo Focus Workspace Extension?

- ❌ Requires npm/yarn workspaces (JavaScript-only)
- ❌ Not designed for ad-hoc, non-package "workspaces"
- ❌ Doesn't fit multi-language monorepos

### Why Not `.code-workspace` Files?

- ❌ Static - need to create separate workspace file for each example
- ❌ Switching requires opening different workspace (disrupts flow)
- ✅ Our solution is dynamic and script-driven

### Why Not Just Open New VSCode Window?

- ❌ Loses context (git history, search history, etc.)
- ❌ Docker compose still needs to run from parent directory
- ❌ Managing multiple windows is tedious

## Troubleshooting

### Focus not working?

1. Make sure you reload VSCode window after first focus: Cmd+Shift+P → "Reload Window"
2. Check `.vscode/settings.json` was created/updated
3. Run `uv run focus status` to verify

### Docker compose not found?

1. Check you're in the correct repo: `echo $UNSAFE_CODE_ROOT`
2. Verify compose.yml exists: `ls $UNSAFE_CODE_ROOT/vulnerabilities/python/flask/confusion/compose.yml`
3. Try with absolute path first

### Short forms not working?

1. Make sure you sourced the helper script: `source tools/dev/unsafe-code-dev.sh`
2. Check `uchelp` command exists: `type uchelp`
3. Restart shell if needed

## Technical Details

### Focus Script Architecture

```
┌─────────────────────┐
│  uv run focus       │
└──────────┬──────────┘
           │
           ↓
┌────────────────────────┐
│ .vscode/settings.json  │ ← Modified
│ {                      │
│   "files.exclude": {   │
│     "r01/": true,      │
│     "r02/e01": true,   │
│     ...                │
│   }                    │
│ }                      │
└────────────────────────┘
           │
           ↓
┌────────────────────────┐
│ VSCode UI (filtered)   │
└────────────────────────┘
```

### Shell Helpers Architecture

```
┌──────────────────────────┐
│ ucfocus r02/e03          │
└──────────┬───────────────┘
           │
           ├─→ Calls uv run focus
           │   └─→ Updates .vscode/settings.json
           │
           └─→ cd to target directory
               └─→ Sets UC_FOCUS_AREA env var
                   └─→ Used by ucup/ucdown/uclogs
```

## Future Enhancements

Possible improvements:
- [ ] Add support for other frameworks (Django, Express, etc.)
- [ ] Create VSCode extension for one-click focusing
- [ ] Add `uctest` command for running tests in focused example
- [ ] Support focusing on multiple examples simultaneously
- [ ] Integration with git worktrees for parallel work

## Contributing

Found a bug or have a feature request? Open an issue or submit a PR!
