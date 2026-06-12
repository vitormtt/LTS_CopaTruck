#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DATE="$(date '+%Y-%m-%d %H:%M')"
STACKS=()
[[ -f "$REPO_ROOT/pyproject.toml" || -f "$REPO_ROOT/requirements.txt" ]] && STACKS+=("python")
[[ -f "$REPO_ROOT/docker-compose.yml" || -f "$REPO_ROOT/Dockerfile" ]] && STACKS+=("docker")
[[ -f "$REPO_ROOT/package.json" ]] && STACKS+=("node")
[[ $(find "$REPO_ROOT" -name "*.prj" -maxdepth 3 2>/dev/null | head -1) ]] && STACKS+=("matlab")
STACK_STR=$(IFS=,; echo "${STACKS[*]:-unknown}")
echo "=== SARU SessionStart ==="
echo "repo: $(basename "$REPO_ROOT")"
echo "stack: $STACK_STR"
echo "data: $DATE"
echo "========================="
AGENTS_FILE="$REPO_ROOT/AGENTS.md"
if [[ -f "$AGENTS_FILE" ]]; then
  sed -i "s/last_updated: .*/last_updated: \"$DATE\"/" "$AGENTS_FILE" 2>/dev/null || true
fi
