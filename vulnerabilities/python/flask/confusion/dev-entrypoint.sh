#!/usr/bin/env bash
set -euo pipefail

# Paths to watch (comma-separated). Override per project if needed.
WATCH_PATHS_RAW="${DEV_WATCH:-/app}"

IFS=',' read -r -a paths <<< "$WATCH_PATHS_RAW"
WATCH_ARGS=()
for path in "${paths[@]}"; do
  # Add -w flag followed by the path
  WATCH_ARGS+=("-w" "$path")
done
# --- End of Fix ---

# Determine the dev command:
# 1) If CMD/command is passed in, use that.
# 2) Else, if DEV_CMD env var is set, parse it as a shell-like string.
if [[ "$#" -gt 0 ]]; then
  DEV_CMD=("$@")
elif [[ -n "${DEV_CMD:-}" ]]; then
  # shellcheck disable=SC2206
  DEV_CMD=(${DEV_CMD})
else
  echo "[dev-entrypoint] No command provided (via CMD or DEV_CMD)" >&2
  exit 1
fi

echo "[dev-entrypoint] watch args: ${WATCH_ARGS[*]}"
echo "[dev-entrypoint] dev command: ${DEV_CMD[*]}"

# Hand off to the Python supervisor as PID 1
# -u = unbuffered python output (critical for logs)
# "${WATCH_ARGS[@]}" = expands to -w /path1 -w /path2
# -- = separates supervisor args from the command to run
# "${DEV_CMD[@]}" = expands to the command (e.g., flask run ...)
exec python -u /usr/local/bin/dev-supervisor.py "${WATCH_ARGS[@]}" -- "${DEV_CMD[@]}"
