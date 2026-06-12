#!/usr/bin/env bash
INPUT="$(cat)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
STACKS=()
[[ -f "$REPO_ROOT/pyproject.toml" || -f "$REPO_ROOT/requirements.txt" ]] && STACKS+=("python")
[[ -f "$REPO_ROOT/docker-compose.yml" || -f "$REPO_ROOT/Dockerfile" ]] && STACKS+=("docker")
[[ -f "$REPO_ROOT/package.json" ]] && STACKS+=("node")
[[ $(find "$REPO_ROOT" -name "*.prj" -maxdepth 3 2>/dev/null | head -1) ]] && STACKS+=("matlab")
STACK_STR=$(IFS=,; echo "${STACKS[*]:-unknown}")
echo "[UserPromptSubmit] stack=[$STACK_STR] repo=$(basename "$REPO_ROOT")"
