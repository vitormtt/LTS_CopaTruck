---
name: python-saru-standards
description: >
  Enforces SARU Dynamics Python coding conventions across all products:
  SARU Course (Copa Truck), SARU Sim (StockCar, Generic), SARU Analyze (LapAnalyzer).
---
## Quando acionar
Qualquer arquivo Python novo ou revisado neste repo.

## Convenções SARU Python

### Estrutura
- Layout `src/`: `src/<pkg>/` com `__init__.py` exportando apenas interface pública
- `pyproject.toml` como SSoT: build, deps, ruff, mypy, pytest
- Testes em `tests/unit/`, `tests/integration/`

### Tipagem
- Type hints obrigatórios em toda função/método público
- `from __future__ import annotations` no topo
- `mypy --strict`: zero `# type: ignore` sem comentário justificando

### OOP
- `@dataclass` para parâmetros e resultados; `frozen=True` para value objects
- `ABC` para subsistemas intercambiáveis (Solver, TireModel, TrackLoader)
- Composição > herança; `LapSimulator` contém Vehicle/Track/Solver, nunca herda
- `__repr__` obrigatório em todos os dataclasses
- Atributos privados com `_prefix`; interface pública via `@property`

### Numérico / Física
- Zero magic numbers: constantes nomeadas no topo do módulo ou em `config/`
- NumPy vetorização > loops Python para arrays
- SI throughout (m, kg, s, rad); conversões explícitas e documentadas
- `hypothesis` para property-based tests em invariantes numéricas

### Git
- Conventional Commits: `feat/fix/refactor/sim/docs/chore/test/perf`
- Nunca `--no-verify`
- `pytest` deve passar 100% antes de qualquer commit proposto

### Proibições
- Hardcode de parâmetros de veículo, pista ou calendário fora de YAML/JSON/HDF5
- `except Exception: pass`
- `print()` em código de produção (use `logging`)
- `globals().update`, `exec`, `eval` em produção
