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
  "chmod 777"
  "chmod -R 777"
)
for PATTERN in "${BLOCKLIST[@]}"; do
  if echo "$COMMAND" | grep -qF "$PATTERN"; then
    echo "BLOCKED: comando proibido detectado: $PATTERN" >&2
    exit 1
  fi
done
# padrões com variação (regex): download canalizado para shell
if echo "$COMMAND" | grep -Eq '(curl|wget)[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(ba|z)?sh'; then
  echo "BLOCKED: download canalizado para shell (curl|sh) — baixe, inspecione, depois execute" >&2
  exit 1
fi
