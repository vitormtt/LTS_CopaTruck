# AGENTS.md — LapTimeSimulator_CopaTruck (SARU Course)

last_updated: "2026-05-25 00:00"

## Stack fingerprint

- python: ✓ (pyproject.toml)
- streamlit: ✓ (src/visualization/interface.py)
- docker: ✗
- matlab: ✗

## Trio de agentes SARU

| Agente | Ferramenta | Quando usar |
|--------|-----------|-------------|
| Claude Code | claude code | implementação, debug, refactor, análise |
| Antigravity | antigravity | tarefas longas, background |
| OpenCode | opencode | BACKLOG — não usar ainda |

## Sub-agents disponíveis

| Agente | Arquivo | Quando usar |
|--------|---------|-------------|
| `code-reviewer` | `.claude/agents/code-reviewer.md` | PRs, refatorações |
| `bug-hunter` | `.claude/agents/bug-hunter.md` | root cause obscuro |
| `docs-curator` | `.claude/agents/docs-curator.md` | sync PDFs / NotebookLM |
| `security-guard` | `.claude/agents/security-guard.md` | auth, I/O, parse externos |
| `architect` | `.claude/agents/architect.md` | novas features, design de módulos |
| `tdd-enforcer` | `.claude/agents/tdd-enforcer.md` | qualquer feature nova |
| `low-cost-runner` | `.claude/agents/low-cost-runner.md` | leitura/busca/catalogação (Haiku) |

## Aprendizados desta sessão

- Hooks bash configurados (session-start, user-prompt-submit, pre-tool-use-bash, cost-guard, stop)
- @imports estáticos em CLAUDE.md substituem hook de injeção de stack rules
- NotebookLM pendente de inicialização (notebook_id vazio em sources.yaml)
- Solver two-pass: nunca alterar sem cross-validation
