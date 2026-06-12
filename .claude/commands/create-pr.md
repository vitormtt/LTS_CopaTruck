---
name: create-pr
description: Abre PR da branch atual para main via gh CLI. Nunca executar sem instrução explícita do Vitor.
---
## Passos
1. Confirmar branch: `git branch --show-current`
2. Checar diff: `git log main..HEAD --oneline`
3. Perguntar ao Vitor: título + descrição do PR
4. `gh pr create --title "..." --body "..." --base main`

PROIBIDO: abrir PR sem pedido explícito do Vitor.
