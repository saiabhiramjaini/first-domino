#!/usr/bin/env bash
# Formats and lints a Python file right after an agent edits it. Exit code 2 sends ruff's findings back to the agent.
set -uo pipefail

file=$(jq -r '.tool_input.file_path // empty')
[[ "$file" == *.py ]] || exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

uv run --quiet ruff format "$file" >/dev/null 2>&1
if ! findings=$(uv run --quiet ruff check --fix "$file" 2>&1); then
  echo "$findings" >&2
  exit 2
fi
