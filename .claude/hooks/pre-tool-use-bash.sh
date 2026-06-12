#!/usr/bin/env bash
INPUT="$(cat)"
COMMAND="$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('input',{}).get('command',''))" 2>/dev/null || echo "")"
BLOCKLIST=(
  "rm -rf /"
  "git push --force"
  "git push -f "
  "git reset --hard"
  "docker rm -f"
  "docker system prune"
  "dd if=/dev/"
)
for PATTERN in "${BLOCKLIST[@]}"; do
  if echo "$COMMAND" | grep -qF "$PATTERN"; then
    echo "BLOCKED: comando proibido detectado: $PATTERN" >&2
    exit 1
  fi
done
