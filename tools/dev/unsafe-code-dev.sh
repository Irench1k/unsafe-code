#!/usr/bin/env bash
# Unsafe Code Lab - Development Helper Functions
# Source this file in your shell: source tools/dev/unsafe-code-dev.sh
# Or add to ~/.zshrc or ~/.bashrc: source /path/to/unsafe-code/tools/dev/unsafe-code-dev.sh

# Get repo root (works for bash/zsh sourcing)
_uc_script_source="${BASH_SOURCE[0]:-${(%):-%N}}"
_uc_script_dir="$(cd "$(dirname "$_uc_script_source")" && pwd)"
export UNSAFE_CODE_ROOT="$(cd "$_uc_script_dir/../.." && pwd)"

# Track current focus area
export UC_FOCUS_AREA=""

_uc_focus_cli() {
    (cd "$UNSAFE_CODE_ROOT" && uv run focus "$@")
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

    # If short form like "r02/e03", expand it
    if [[ "$target" =~ ^r[0-9]+/?e?[0-9]*$ ]]; then
        # Find the full path
        local webapp_base="$UNSAFE_CODE_ROOT/vulnerabilities/python/flask/confusion/webapp"

        # Parse r02/e03 format
        if [[ "$target" =~ ^(r[0-9]+)/(e[0-9]+)$ ]]; then
            local round="${BASH_REMATCH[1]}"
            local example="${BASH_REMATCH[2]}"
            # Find the full directory name (e.g., r02_authentication_confusion)
            local round_dir=$(ls -d "$webapp_base/${round}"* 2>/dev/null | head -1)
            if [[ -n "$round_dir" ]]; then
                target="$round_dir/$example"
            fi
        elif [[ "$target" =~ ^(r[0-9]+)$ ]]; then
            # Just round, no example
            local round="${BASH_REMATCH[1]}"
            local round_dir=$(ls -d "$webapp_base/${round}"* 2>/dev/null | head -1)
            if [[ -n "$round_dir" ]]; then
                target="$round_dir"
            fi
        fi
    fi

    # If relative path, make it absolute
    if [[ "$target" != /* ]]; then
        target="$UNSAFE_CODE_ROOT/$target"
    fi

    # Run focus script via uv
    _uc_focus_cli "$target"

    if [[ $? -eq 0 ]]; then
        export UC_FOCUS_AREA="$target"
        # Also cd to that directory
        cd "$target"
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
    (cd "$compose_dir" && docker compose down "$@")
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

# Quick jump to round/example (e.g., "ucgo r02/e03" or full names)
ucgo() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: ucgo <round>/<example>"
        echo "Example: ucgo r02/e03"
        return 1
    fi

    local target="$1"
    local webapp_base="$UNSAFE_CODE_ROOT/vulnerabilities/python/flask/confusion/webapp"

    # Allow passing full relative paths (vulnerabilities/...)
    if [[ -d "$UNSAFE_CODE_ROOT/$target" ]]; then
        cd "$UNSAFE_CODE_ROOT/$target"
        echo "📂 $(pwd)"
        return 0
    fi

    local round_token="${target%%/*}"
    local example_token="${target#*/}"
    if [[ -z "$example_token" || "$round_token" == "$target" ]]; then
        echo "❌ Invalid format. Use: ucgo r02/e03"
        return 1
    fi
    if [[ ! "$round_token" =~ ^r[0-9]+ ]]; then
        echo "❌ Invalid round format. Use: ucgo r02/e03"
        return 1
    fi
    if [[ ! "$example_token" =~ ^e[0-9]+ ]]; then
        echo "❌ Invalid example format. Use: ucgo r02/e03"
        return 1
    fi
    local round_dir=""

    if [[ -d "$webapp_base/$round_token" ]]; then
        round_dir="$webapp_base/$round_token"
    elif [[ "$round_token" =~ ^r[0-9]+$ ]]; then
        round_dir=$(command find "$webapp_base" -maxdepth 1 -mindepth 1 -type d -name "${round_token}_*" | head -1)
    fi

    if [[ -z "$round_dir" ]]; then
        echo "❌ Could not find round: $round_token"
        return 1
    fi

    local example_dir=""
    if [[ -d "$round_dir/$example_token" ]]; then
        example_dir="$round_dir/$example_token"
    elif [[ "$example_token" =~ ^e[0-9]+$ ]]; then
        example_dir=$(command find "$round_dir" -maxdepth 1 -mindepth 1 -type d -name "${example_token}_*" | head -1)
    fi

    if [[ -z "$example_dir" ]]; then
        echo "❌ Could not find example: $example_token in $(basename "$round_dir")"
        return 1
    fi

    cd "$example_dir"
    echo "📂 $(pwd)"
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

Focus Management:
  ucfocus r02/e03        Focus VSCode on round 2, example 3
  ucfocus <full-path>    Focus on any directory
  ucunfocus              Clear focus (show all files)
  ucstatus               Show current focus

Docker Compose (auto-finds compose.yml):
  ucup                   docker compose up --build
  ucdown                 docker compose down
  uclogs                 docker compose logs -f

Navigation:
  uc                     Jump to repo root
  ucflask                Jump to Flask confusion directory
  ucwebapp               Jump to webapp directory
  ucgo r02/e03           Jump to specific round/example
  uclist                 List examples in current round

Combined Workflow:
  ucfocus r02/e03        1. Focus VSCode on example
                         2. Navigate to that directory
  ucup                   3. Start docker compose (finds compose.yml automatically)

  # Work on your code...

  ucdown                 4. Stop docker compose
  ucunfocus              5. Clear focus when done

EOF
}
