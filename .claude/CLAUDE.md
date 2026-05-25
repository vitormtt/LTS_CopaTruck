# .claude/CLAUDE.md — LapTimeSimulator_CopaTruck (SARU Course)

> Complementa o `CLAUDE.md` da raiz e o global `~/.claude/CLAUDE.md`. Carregado automaticamente em toda sessão.

## Ordem de precedência

1. Instruções do prompt atual (mais forte)
2. `.claude/rules/<stack>.md` (imports estáticos declarados em CLAUDE.md raiz)
3. `.claude/CLAUDE.md` (este arquivo)
4. `CLAUDE.md` da raiz do repo
5. `~/.claude/CLAUDE.md` (global do usuário, mais fraco)

Em caso de conflito, o contexto **mais específico** vence.

## Workflow obrigatório

1. **Antes de editar**: ler arquivo, verificar testes existentes, entender módulo.
2. **Durante edição**: seguir `rules/python.md` e `rules/streamlit.md`; zero magic numbers.
3. **Após edição**: rodar `/lint-and-validate` ou `/quality-gate` (lint + type-check + testes).
4. **Commits**: Conventional Commits (`feat/fix/chore/refactor/sim/docs/test`). Nunca `--no-verify`.

## Skills disponíveis

| Skill | Arquivo | Quando acionar |
|---|---|---|
| `python-saru-standards` | `.claude/skills/python-saru-standards.md` | qualquer arquivo Python novo/revisão |
| `python-solver-workflow` | `.claude/skills/python-solver-workflow.md` | solver LTS, grip limits, cross-validation |
| `lint-and-validate` | `.claude/commands/lint-and-validate.md` | antes de commit; CI falhou |
| `create-pr` | `.claude/commands/create-pr.md` | hora de abrir PR |
| `/tdd` | `.claude/commands/tdd.md` | features novas com comportamento observável |
| `/quality-gate` | `.claude/commands/quality-gate.md` | lint-and-validate + cobertura ≥85% |

## Sub-agents disponíveis

| Agente | Arquivo | Quando usar |
|---|---|---|
| `code-reviewer` | `.claude/agents/code-reviewer.md` | PRs, refatorações |
| `bug-hunter` | `.claude/agents/bug-hunter.md` | root cause obscuro |
| `docs-curator` | `.claude/agents/docs-curator.md` | sync PDFs / NotebookLM |
| `security-guard` | `.claude/agents/security-guard.md` | auth, I/O, parse externos |
| `architect` | `.claude/agents/architect.md` | novas features, design de módulos |
| `tdd-enforcer` | `.claude/agents/tdd-enforcer.md` | qualquer feature nova |
| `low-cost-runner` | `.claude/agents/low-cost-runner.md` | leitura/busca/catalogação (Haiku) |

## NotebookLM (pendente inicialização)

sources.yaml lista os PDFs do projeto. Para ativar:
1. Criar notebook em notebooklm.google.com
2. Preencher `notebook_id` em `.claude/docs/sources.yaml`
3. Rodar `/notebooklm-ingest` para ingerir os PDFs de `docs/`

Até inicialização: NÃO usar `/research` ou `/notebooklm-ingest` (retornam erro de guard).

## Proibições

- Hardcode de parâmetros de veículo ou pista fora de YAML/JSON/HDF5.
- Commitar `.env`, `*.credentials*`, PDFs técnicos.
- `git push --force` / `git reset --hard` / `rm -rf` sem instrução explícita do Vitor.
- Criar abstração nova quando 2 implementações concretas resolvem o problema.
- Alterar two-pass solver sem cross-validation prévia.
