#!/bin/bash
# =============================================================================
# Unsafe Code Lab - Claude Code Shell Initialization
# =============================================================================
#
# PROBLEM: Claude Code's shell snapshot mechanism filters out underscore-prefixed
# functions (like _uc_find_compose_dir). The public functions (uclogs, ucup, etc.)
# depend on these helpers and fail at runtime with "command not found".
#
# SOLUTION: Source the tools directly via CLAUDE_ENV_FILE, bypassing the snapshot.
#
# SETUP: Add this to your .envrc (already included in template):
#
#   export CLAUDE_ENV_FILE="${PWD}/.claude/shell-init.sh"
#
# Then restart Claude Code in the project directory.
# =============================================================================

# Derive project root from CLAUDE_ENV_FILE (which points to this script)
# CLAUDE_ENV_FILE = /path/to/project/.claude/shell-init.sh
# Project root    = /path/to/project
UNSAFE_CODE_ROOT="${CLAUDE_ENV_FILE%/.claude/shell-init.sh}"

source "$UNSAFE_CODE_ROOT/tools/dev/unsafe-code-dev.sh"
