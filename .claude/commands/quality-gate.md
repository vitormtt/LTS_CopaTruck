---
name: quality-gate
description: Alias de lint-and-validate com gate de cobertura (≥85%).
---
## Passos
1. Executar lint-and-validate completo
2. `pytest --cov=src --cov-fail-under=85`

Gate: coverage < 85% bloqueia commit.
