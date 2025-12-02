#!/usr/bin/env bash
# Unsafe Code Lab - Development Helper Functions
# Source this file in your shell: source tools/dev/unsafe-code-dev.sh
# Or add to ~/.zshrc or ~/.bashrc: source /path/to/unsafe-code/tools/dev/unsafe-code-dev.sh

# Get repo root (works for bash/zsh sourcing)
_uc_script_source="${BASH_SOURCE[0]:-${(%):-%N}}"
_uc_script_dir="$(cd "$(dirname "$_uc_script_source")" && pwd)"
export UNSAFE_CODE_ROOT="$(cd "$_uc_script_dir/../.." && pwd)"

# ================================
# Node.js Environment
# ================================
# uctest is now an npm package - ensure node_modules/.bin is available
export PATH="$UNSAFE_CODE_ROOT/node_modules/.bin:$PATH"

# Track current focus area
export UC_FOCUS_AREA=""
# Store helpful error message and resolved path for the last match attempt
UC_LAST_MATCH_ERROR=""
UC_MATCHED_PATH=""

_uc_focus_cli() {
    (cd "$UNSAFE_CODE_ROOT" && uv run focus "$@")
}

_uc_abs_path() {
    local dir="$1"
    (cd "$dir" 2>/dev/null && pwd)
}

_uc_resolve_target_path() {
    local target="$1"
    local require_example="${2:-0}"
    local usage_hint="${3:-ucgo}"
    UC_LAST_MATCH_ERROR=""
    UC_MATCHED_PATH=""

    if [[ -z "$target" ]]; then
        UC_MATCHED_PATH="$UNSAFE_CODE_ROOT"
        return 0
    fi

    if [[ -d "$target" ]]; then
        UC_MATCHED_PATH="$(_uc_abs_path "$target")"
        return 0
    fi

    if [[ -d "$UNSAFE_CODE_ROOT/$target" ]]; then
        UC_MATCHED_PATH="$(_uc_abs_path "$UNSAFE_CODE_ROOT/$target")"
        return 0
    fi

    local round_token="${target%%/*}"
    local example_token=""

    if [[ "$target" != "$round_token" ]]; then
        example_token="${target#*/}"
    fi

    if [[ -z "$example_token" ]]; then
        if [[ "$require_example" -eq 1 ]]; then
            UC_LAST_MATCH_ERROR="❌ Invalid format. Use: $usage_hint r02/e03"
            return 1
        fi
    fi

    if [[ ! "$round_token" =~ ^r[0-9]+$ ]]; then
        UC_LAST_MATCH_ERROR="❌ Invalid round format. Use: $usage_hint r02/e03"
        return 1
    fi

    if [[ -n "$example_token" && ! "$example_token" =~ ^e[0-9]+$ ]]; then
        UC_LAST_MATCH_ERROR="❌ Invalid example format. Use: $usage_hint r02/e03"
        return 1
    fi

    local webapp_base="$UNSAFE_CODE_ROOT/vulnerabilities/python/flask/confusion/webapp"
    local round_dir=""
    if [[ -d "$webapp_base/$round_token" ]]; then
        round_dir="$webapp_base/$round_token"
    else
        round_dir=$(command find "$webapp_base" -maxdepth 1 -mindepth 1 -type d -name "${round_token}_*" | head -1)
    fi

    if [[ -z "$round_dir" ]]; then
        UC_LAST_MATCH_ERROR="❌ Could not find round: $round_token"
        return 1
    fi

    if [[ -z "$example_token" ]]; then
        UC_MATCHED_PATH="$round_dir"
        return 0
    fi

    local example_dir=""
    if [[ -d "$round_dir/$example_token" ]]; then
        example_dir="$round_dir/$example_token"
    else
        example_dir=$(command find "$round_dir" -maxdepth 1 -mindepth 1 -type d -name "${example_token}_*" | head -1)
    fi

    if [[ -z "$example_dir" ]]; then
        UC_LAST_MATCH_ERROR="❌ Could not find example: $example_token in $(basename "$round_dir")"
        return 1
    fi

    UC_MATCHED_PATH="$example_dir"
    return 0
}

# ================================
# Focus Management
# ================================

# Focus on a specific example/directory
ucfocus() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: ucfocus <path-to-directory>"
        echo "Example: ucfocus r02/e03"
        echo "         ucfocus vulnerabilities/python/flask/confusion/webapp/r02_authentication_confusion/e03_fake_header_refund"
        return 1
    fi

    local target="$1"
    if ! _uc_resolve_target_path "$target" 0 ucfocus; then
        if [[ -n "$UC_LAST_MATCH_ERROR" ]]; then
            echo "$UC_LAST_MATCH_ERROR"
        fi
        return 1
    fi

    local resolved="$UC_MATCHED_PATH"

    _uc_focus_cli "$resolved"

    if [[ $? -eq 0 ]]; then
        export UC_FOCUS_AREA="$resolved"
        # Also cd to that directory
        cd "$resolved"
    fi
}

# Reset focus
ucunfocus() {
    _uc_focus_cli reset
    export UC_FOCUS_AREA=""
    echo "✅ Focus cleared"
}

# Show current focus
ucstatus() {
    _uc_focus_cli status
    if [[ -n "$UC_FOCUS_AREA" ]]; then
        echo "📍 Current directory: $(pwd)"
    fi
}

# ================================
# Docker Compose Shortcuts
# ================================

# Run docker compose from the correct location
# Works regardless of current directory
ucup() {
    local compose_dir=""

    # Determine which compose.yml to use based on focus or current directory
    if [[ -n "$UC_FOCUS_AREA" ]]; then
        # Find compose.yml by walking up from focus area
        local search_dir="$UC_FOCUS_AREA"
        while [[ "$search_dir" != "/" && "$search_dir" != "$UNSAFE_CODE_ROOT" ]]; do
            if [[ -f "$search_dir/compose.yml" ]] || [[ -f "$search_dir/docker-compose.yml" ]]; then
                compose_dir="$search_dir"
                break
            fi
            search_dir="$(dirname "$search_dir")"
        done
    fi

    # Fallback: use current directory
    if [[ -z "$compose_dir" ]]; then
        local search_dir="$(pwd)"
        while [[ "$search_dir" != "/" ]]; do
            if [[ -f "$search_dir/compose.yml" ]] || [[ -f "$search_dir/docker-compose.yml" ]]; then
                compose_dir="$search_dir"
                break
            fi
            search_dir="$(dirname "$search_dir")"
        done
    fi

    if [[ -z "$compose_dir" ]]; then
        echo "❌ Could not find compose.yml in current path"
        return 1
    fi

    echo "🐳 Running docker compose from: $compose_dir"
    (cd "$compose_dir" && docker compose up --build "$@")
}

# Docker compose down
ucdown() {
    local compose_dir=""

    if [[ -n "$UC_FOCUS_AREA" ]]; then
        local search_dir="$UC_FOCUS_AREA"
        while [[ "$search_dir" != "/" && "$search_dir" != "$UNSAFE_CODE_ROOT" ]]; do
            if [[ -f "$search_dir/compose.yml" ]] || [[ -f "$search_dir/docker-compose.yml" ]]; then
                compose_dir="$search_dir"
                break
            fi
            search_dir="$(dirname "$search_dir")"
        done
    fi

    if [[ -z "$compose_dir" ]]; then
        local search_dir="$(pwd)"
        while [[ "$search_dir" != "/" ]]; do
            if [[ -f "$search_dir/compose.yml" ]] || [[ -f "$search_dir/docker-compose.yml" ]]; then
                compose_dir="$search_dir"
                break
            fi
            search_dir="$(dirname "$search_dir")"
        done
    fi

    if [[ -z "$compose_dir" ]]; then
        echo "❌ Could not find compose.yml in current path"
        return 1
    fi

    echo "🐳 Running docker compose down from: $compose_dir"
    (cd "$compose_dir" && docker compose down --volumes --remove-orphans "$@")
}

# Docker compose logs
uclogs() {
    local compose_dir=""

    if [[ -n "$UC_FOCUS_AREA" ]]; then
        local search_dir="$UC_FOCUS_AREA"
        while [[ "$search_dir" != "/" && "$search_dir" != "$UNSAFE_CODE_ROOT" ]]; do
            if [[ -f "$search_dir/compose.yml" ]] || [[ -f "$search_dir/docker-compose.yml" ]]; then
                compose_dir="$search_dir"
                break
            fi
            search_dir="$(dirname "$search_dir")"
        done
    fi

    if [[ -z "$compose_dir" ]]; then
        local search_dir="$(pwd)"
        while [[ "$search_dir" != "/" ]]; do
            if [[ -f "$search_dir/compose.yml" ]] || [[ -f "$search_dir/docker-compose.yml" ]]; then
                compose_dir="$search_dir"
                break
            fi
            search_dir="$(dirname "$search_dir")"
        done
    fi

    if [[ -z "$compose_dir" ]]; then
        echo "❌ Could not find compose.yml in current path"
        return 1
    fi

    (cd "$compose_dir" && docker compose logs -f "$@")
}

# ================================
# Quick Navigation
# ================================

# Jump to common locations
alias uc='cd $UNSAFE_CODE_ROOT'
alias ucflask='cd $UNSAFE_CODE_ROOT/vulnerabilities/python/flask/confusion'
alias ucwebapp='cd $UNSAFE_CODE_ROOT/vulnerabilities/python/flask/confusion/webapp'
alias ucspecs='cd $UNSAFE_CODE_ROOT/spec'

# Quick jump to round/example (e.g., "ucgo r02/e03" or full names)
ucgo() {
    if [[ $# -eq 0 ]]; then
        cd "$UNSAFE_CODE_ROOT"
        echo "📂 $(pwd)"
        return 0
    fi

    local target="$1"
    if ! _uc_resolve_target_path "$target" 1 ucgo; then
        if [[ -n "$UC_LAST_MATCH_ERROR" ]]; then
            echo "$UC_LAST_MATCH_ERROR"
        fi
        return 1
    fi

    local resolved="$UC_MATCHED_PATH"

    cd "$resolved"
    echo "📂 $(pwd)"
}

# ================================
# Spec Suite Management
# ================================

# Generate inherited e2e spec files based on spec.yml
# Usage: ucsync [versions...] [-n|--dry-run] [-v|--verbose]
#        ucsync clean [versions...]
ucsync() {
    (cd "$UNSAFE_CODE_ROOT" && uv run ucsync "$@")
}

# ================================
# E2E Spec Testing
# ================================

# E2E spec test runner - uses uctest npm package
# Use `npx uctest --help` for full documentation
uctest() {
    (cd "$UNSAFE_CODE_ROOT/spec" && npx uctest "$@")
}

# E2E spec linter - checks for jurisdiction violations, fake tests, etc.
# Use `uv run uclint --help` for full documentation
uclint() {
    (cd "$UNSAFE_CODE_ROOT" && uv run uclint "$@")
}

# ================================
# Helpful Aliases
# ================================

# List all examples in current round
uclist() {
    local search_dir="$(pwd)"

    # Find the round directory
    while [[ "$search_dir" != "/" ]]; do
        if [[ $(basename "$search_dir") =~ ^r[0-9]+_ ]]; then
            echo "📚 Examples in $(basename "$search_dir"):"
            ls -d "$search_dir"/e* 2>/dev/null | while read -r example; do
                echo "  - $(basename "$example")"
            done
            return 0
        fi
        search_dir="$(dirname "$search_dir")"
    done

    echo "❌ Not in a round directory"
    return 1
}

# ================================
# Status Display
# ================================

# Show helpful status info
uchelp() {
    cat << 'EOF'
🔧 Unsafe Code Lab - Development Helpers

E2E Spec Testing (fail-fast by default):
  uctest                 Run tests (stops on first failure)
  uctest --resume        Run again to resume from failure
  uctest -k              Run all tests (keep going after failures)
  uctest @vulnerable     Run tests tagged 'vulnerable'
  uctest @v301 @vulnerable Run tests with BOTH tags (AND logic)
  uctest :checkout       Run test named 'checkout'
  uctest v301/orders     Run tests in specific path
  uctest -a              Run all tests (default mode executes minimal subset)

  (Uses npm package from github:execveat/uctest)

Spec Linting:
  uclint                 Lint spec suite for violations
  uclint v302            Lint specific version
  uclint --all           Lint all versions
  uclint --strict        Exit non-zero on any issue (for CI)

Focus Management:
  ucfocus r02/e03        Focus VSCode on round 2, example 3
  ucfocus <full-path>    Focus on any directory
  ucunfocus              Clear focus (show all files)
  ucstatus               Show current focus

Docker Compose (auto-finds compose.yml):
  ucup                   docker compose up --build
  ucup -d                docker compose up --build --detach
  ucdown                 docker compose down
  uclogs                 docker compose logs -f

Navigation:
  uc                     Jump to repo root
  ucflask                Jump to Flask confusion directory
  ucwebapp               Jump to webapp directory
  ucspecs                Jump to e2e spec directory
  ucgo r02/e03           Jump to specific round/example
  uclist                 List examples in current round

Spec Suite Management:
  ucsync                 Generate inherited tests (default action)
  ucsync v302            Generate for specific version
  ucsync -n              Preview changes (dry-run)
  ucsync clean           Remove all inherited files

Typical Development Workflow:
  1. ucfocus r02/e03      # Focus VSCode + cd to example
  2. ucup -d              # Start services in background
  3. uctest               # Run tests (fail-fast)
  4. # Fix code...
  5. uctest               # Resume from failure
  6. ucdown && ucunfocus  # Cleanup when done

EOF
}
