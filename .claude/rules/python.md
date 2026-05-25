# Rules — Python

Padrões modernos Python 3.11+ para projetos SARU/pessoais. Foco em **prevenção de bugs**, manutenibilidade, performance.

## Padrões de código

- **PEP 8** estrito via `ruff` (config em `pyproject.toml`).
- **Type hints obrigatórios** em assinaturas de funções/métodos públicos. Use `from __future__ import annotations`.
- `mypy --strict` como baseline. Nunca `# type: ignore` sem comentário explicando a razão e a issue.
- Docstrings em estilo **NumPy** ou **Google** (consistência por projeto); obrigatórias em classes e métodos públicos.
- **Zero magic numbers**: constantes nomeadas no topo do módulo ou em `config/`.
- **Zero imports de `*`**; imports absolutos; ordem `stdlib → third-party → local` (ruff/isort enforça).

## OOP & estruturas de dados

- `@dataclass(frozen=True)` para value objects imutáveis; `@dataclass(slots=True)` para hot path.
- Herança apenas quando há IS-A real; composição preferida.
- Encapsulamento: atributos privados com `_prefix`; interface pública via `@property`.
- Protocols (`typing.Protocol`) para duck typing tipado em vez de ABCs quando possível.

## Funções

- Máx. **3–4 argumentos posicionais**; acima disso, `@dataclass` de parâmetros ou kwargs-only (`*`).
- Funções puras > funções com efeito colateral. Separe I/O de lógica.
- Evite mutação de argumentos (inputs imutáveis por default).
- Return types explícitos. `-> None` explícito em procedures.

## Estrutura do projeto

```
src/<pkg>/           # código fonte (layout src/ preferido)
tests/               # pytest
docs/                # gerados via mkdocs ou sphinx (opcional)
pyproject.toml       # SSoT de build, deps, ruff, mypy, pytest
.python-version      # pin da versão
```

## Testes (pytest)

- Estrutura: `tests/unit/`, `tests/integration/`.
- **Nomenclatura**: `test_<funcao>_<condicao>_<esperado>`.
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`.
- Fixtures em `conftest.py` por escopo mais apertado possível.
- Evitar mocks em lógica de domínio; mock só em **boundaries** (HTTP, filesystem, DB externo).
- **Coverage ≥ 85%** em módulos de domínio.
- Property-based: `hypothesis` para invariantes numéricas (útil em simulação).

## Performance

- Perfilar antes de otimizar (`cProfile`, `py-spy`, `line_profiler`).
- NumPy vetorização > loops Python puros para arrays numéricos.
- Use `functools.lru_cache` para funções puras caras.

## Antipadrões proibidos

- `except Exception: pass` — sempre logar e re-raise ou tratar específico.
- Mutable default arguments (`def f(x=[])`).
- Comparar com `== None`, `== True` (use `is None`, `if x:`).
- `print()` em código de produção (use `logging`).
- `globals().update(...)` / uso criativo de `exec`/`eval`.
