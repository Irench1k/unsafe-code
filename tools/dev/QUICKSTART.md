# Quick Start: Focus on Flask Confusion Examples

## Problem You're Solving

When working on `r02/e03`, VSCode suggests files from `r01/e01` or other examples. Annoying!

## Solution: 2 Minutes to Setup

### Step 1: Add to Your Shell Config

Add this ONE line to `~/.zshrc` (or `~/.bashrc`):

```bash
source /path/to/unsafe-code/tools/dev/unsafe-code-dev.sh
```

Then reload: `source ~/.zshrc`

### Step 2: Try It

```bash
# Focus on r02/e03
ucfocus r02/e03

# Start docker compose (works from anywhere!)
ucup

# See the magic!
# - VSCode only shows r02/e03 files
# - No more wrong autocomplete suggestions
# - Docker compose runs from correct directory
```

Done! 🎉

## Daily Workflow

```bash
# Morning: Start working on new example
ucfocus r02/e04
ucup

# ... code all day with perfect autocomplete ...

# Evening: Clean up
ucdown
ucunfocus
```

## All Commands

| Command | What It Does |
|---------|-------------|
| `ucfocus r02/e03` | Focus VSCode + navigate there |
| `ucunfocus` | Show all files again |
| `ucup` | Start docker (finds compose.yml) |
| `ucdown` | Stop docker |
| `ucgo r02/e03` | Jump to example (no focus) |
| `uchelp` | Show all commands |

## Why This Works

- ✅ **VSCode Focus**: Hides other examples using `files.exclude`
- ✅ **Smart Docker**: Auto-finds `compose.yml` by walking up directories
- ✅ **Short Forms**: `r02/e03` instead of long paths
- ✅ **Git-Safe**: `.vscode/` is gitignored

## Troubleshooting

**Commands not found?**
- Did you `source ~/.zshrc`?
- Try: `echo $UNSAFE_CODE_ROOT` (should show repo path)

**Focus not working?**
- Reload VSCode: Cmd+Shift+P → "Reload Window"
- Check: `cat .vscode/settings.json`

**Need more help?**
- Read: `tools/dev/README.md` (full documentation)
- Type: `uchelp`

## Compare: Before vs After

### Before 😞
```bash
# You're here:
cd vulnerabilities/python/flask/confusion/webapp/r02_authentication_confusion/e03_fake_header_refund/routes

# Need to run docker?
cd ../../../../../..  # Ugh, which level?
docker compose up --build

# VSCode suggests:
# - r01_input_source_confusion/e01_dual_parameter/auth.py ❌
# - r02_authentication_confusion/e02_credit_top_ups/auth.py ❌
# - r02_authentication_confusion/e03_fake_header_refund/auth.py ✅ (buried in suggestions)
```

### After 😊
```bash
# You're here:
ucfocus r02/e03        # Focuses + navigates

# Need to run docker?
ucup                   # That's it! Works from anywhere

# VSCode suggests:
# - r02_authentication_confusion/e03_fake_header_refund/auth.py ✅ (ONLY option!)
```

---

**Still reading?** You're ready! Just add that one line to `~/.zshrc` and try `ucfocus r02/e03` 🚀
