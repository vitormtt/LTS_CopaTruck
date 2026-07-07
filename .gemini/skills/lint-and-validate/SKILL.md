---
name: lint-and-validate
description: Executa toolchain completa de validação por stack (lint + type-check + testes). Detecta Python (ruff+mypy+pytest), Node/TS (eslint+tsc+vitest), MATLAB (checkcode+matlab.unittest). Ativa antes de commit, em "/quality-gate", ou quando CI falha.
---

# lint-and-validate

Portão de qualidade. **Tudo tem que passar** antes de considerar uma tarefa concluída.

## Quando acionar

- Antes de qualquer commit.
- Invocada por `/quality-gate`.
- Quando CI reporta falha, para reproduzir localmente.
- Ao final de features TDD.

## Fluxo

### 1. Detectar stack(s)

Verificar presença de:
- `pyproject.toml` ou `setup.py` → **Python**.
- `package.json` com `typescript` ou `tsconfig.json` → **Node/TS**.
- `*.prj` ou `**/*.m` no topo → **MATLAB**.

Pode haver múltiplas stacks no mesmo repo (ex.: backend Python + frontend Next).

### 2. Executar por stack

#### Python

```bash
# lint
ruff check .
# ou equivalente se não tem ruff:
# flake8 . && isort --check . && black --check .

# type-check
mypy src tests --strict

# testes
pytest -q --strict-markers
```

Thresholds:
- ruff: **zero** warnings/errors.
- mypy: **zero** erros (warnings toleráveis com justificativa).
- pytest: **tudo verde**, coverage ≥ 80% em módulos de domínio.

#### Node/TypeScript

```bash
# lint
npx eslint . --max-warnings=0

# type-check
npx tsc --noEmit

# format
npx prettier --check .

# testes
npx vitest run --coverage
```

Thresholds:
- eslint: **zero** warnings (flag `--max-warnings=0`).
- tsc: **zero** erros.
- prettier: tudo formatado.
- vitest: verde + coverage ≥ 80%.

#### MATLAB

```bash
matlab -batch "
    results = runtests('tests', 'IncludeSubfolders', true);
    if any([results.Failed])
        disp(table(results));
        exit(1);
    end
"

# opcional: Code Analyzer em massa
matlab -batch "
    files = dir(fullfile(pwd, '**', '*.m'));
    paths = fullfile({files.folder}, {files.name});
    msgs = checkcode(paths{:});
    if ~isempty([msgs{:}])
        disp(msgs);
        exit(1);
    end
"
```

#### YAML

```bash
yamllint -c .yamllint.yml .
```

### 3. Reportar

Formato de saída esperado:

```
STACK PYTHON
  ✓ ruff check        (0 issues)
  ✓ mypy --strict     (0 errors)
  ✓ pytest            (47 passed, coverage 86%)

STACK TYPESCRIPT
  ✓ eslint            (0 warnings)
  ✓ tsc --noEmit      (0 errors)
  ✓ prettier --check
  ✓ vitest            (23 passed, coverage 82%)

STATUS: PASS
```

Se qualquer degrau falhar:
- Mostrar **exatamente** a saída do tool (não parafrasear).
- Sugerir correção apenas quando trivial e óbvia.
- NÃO tentar auto-fix (`ruff check --fix`, `eslint --fix`) sem pedir — pode introduzir mudanças indesejadas.

## Performance

- Rodar em paralelo quando possível (stacks independentes → background jobs).
- Cache: ruff/mypy/vitest têm caches próprios; não apagar.
- Em monorepo, focar no pacote alterado (`git diff --name-only HEAD~1`).

## Edge cases

- **Sem `dev` deps instaladas**: avisar e sugerir `pip install -e ".[dev]"` / `npm i`.
- **Sem `.venv` ativo (Python)**: usar `python -m` prefix.
- **MATLAB não no PATH**: pular stack MATLAB com warning (não falhar tudo).
- **CI offline**: algumas checks que baixam config (ex.: eslint com extends remoto) podem falhar — documentar.

## Proibições

- Não silenciar warnings com `# noqa`, `// eslint-disable`, `%#ok<*>` sem justificativa em comentário.
- Não commitar com testes vermelhos.
- Não aumentar threshold para fazer passar — resolver a causa.
