---
name: lint-and-validate
description: Roda ruff + mypy + pytest e reporta resultado. Acionar antes de qualquer commit.
---
## Passos
1. `ruff check . --fix` → corrige auto onde possível
2. `mypy src/ --strict` → type check
3. `pytest --tb=short -q` → testes

Resultado: ✅ tudo verde = pode commitar | ❌ = corrigir antes
