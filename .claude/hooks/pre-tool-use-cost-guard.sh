#!/usr/bin/env bash
STATE_FILE=".claude/.sessions/cost-state.json"
mkdir -p ".claude/.sessions"
BUDGET="${CLAUDE_TOKEN_BUDGET:-50000}"
if [[ -f "$STATE_FILE" ]]; then
  USED="$(python3 -c "import json; d=json.load(open('$STATE_FILE')); print(d.get('tokens_used',0))" 2>/dev/null || echo 0)"
  REMAINING=$((BUDGET - USED))
  if [[ "$REMAINING" -lt 5000 ]]; then
    echo "[CostGuard] AVISO: ~$REMAINING tokens restantes nesta sessão (budget: $BUDGET)." >&2
  fi
fi
