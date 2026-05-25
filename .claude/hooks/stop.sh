#!/usr/bin/env bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SESSION_DIR="$REPO_ROOT/.claude/.sessions"
mkdir -p "$SESSION_DIR"
DATE="$(date '+%Y-%m-%d')"
TIMESTAMP="$(date '+%Y-%m-%d %H:%M')"
SESSION_FILE="$SESSION_DIR/$DATE.md"
printf '# Sessão %s\n\n## Objetivo\n<!-- preenchido pelo assistente -->\n\n## Arquivos modificados\n%s\n\n## Resultado\n<!-- preenchido pelo assistente -->\n\n## Próximos passos\n<!-- preenchido pelo assistente -->\n' \
  "$TIMESTAMP" \
  "$(git -C "$REPO_ROOT" diff --name-only HEAD 2>/dev/null || echo 'N/A')" \
  > "$SESSION_FILE"
echo "[Stop] Resumo gravado em $SESSION_FILE"
