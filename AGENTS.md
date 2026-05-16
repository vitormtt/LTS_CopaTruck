# AGENTS.md — Memória Persistente Inter-Sessões

> Padrão: claude-mem / Compound Learning
> **SEMPRE leia este arquivo no início de cada sessão Claude Code.**
> Atualizado automaticamente pelo hook `Stop.ps1` ao final de cada sessão.

---

## Stack Fingerprint

<!-- Preenchido pelo hook SessionStart -->
```yaml
repo: "{{REPO_NAME}}"
stack: []
dependencies: {}
last_updated: ""
```

---

## Project Memory

> Decisões arquiteturais tomadas. Não regredir sem discussão.

<!-- Formato: [DATA] DECISAO: motivo -->
<!-- Exemplo: [2026-04-27] DECISAO: usar SQLite em dev para zero-config; Postgres em prod -->

| Data | Decisão | Motivo |
|------|---------|--------|
| 2026-04-27 | Template v0.2.0 com routing modular | Reduzir tokens por sessão via lazy-load de rules |

---

## Compound Learning

> Padrões descobertos pelo agente ao longo do projeto. Reutilizar antes de reinventar.

<!-- Formato: [CATEGORIA] Padrão descoberto -->

| Categoria | Padrão |
|-----------|--------|
| | |

---

## Session Log

> Últimas sessões resumidas (máx 10 entradas; mais antigas removidas pelo hook).

<!-- Preenchido automaticamente pelo hook Stop.ps1 -->
<!-- Formato:
### [YYYY-MM-DD HH:MM] Sessão N
- Objetivo: ...
- Arquivos modificados: ...
- Resultado: ...
- Próximos passos: ...
-->

### [2026-04-27] Sessão 1
- Objetivo: Refatorar template para ecossistema Multi-stack v0.2.0
- Arquivos modificados: CLAUDE.md, .claude/settings.json, .claude/rules/nestjs.md, .claude/rules/docker.md, AGENTS.md, .claude/agents/*, .claude/hooks/PreToolUse-CostGuard.ps1, .claude/commands/tdd.md, DOCS_TEMPLATE.md
- Resultado: ✅ 12 operações concluídas
- Próximos passos: Testar hook SessionStart com stack detection; calibrar CLAUDE_TOKEN_BUDGET por projeto

---

## Sub-Agents Registry

> Registro de agentes disponíveis e quando acioná-los.

| Agente | Arquivo | Quando usar |
|--------|---------|-------------|
| Code Reviewer | `.claude/agents/code-reviewer.md` | PRs, refatorações grandes |
| Bug Hunter | `.claude/agents/bug-hunter.md` | Bugs com root cause obscuro |
| Docs Curator | `.claude/agents/docs-curator.md` | Sincronizar PDFs com NotebookLM |
| Security Guard | `.claude/agents/security-guard.md` | PRs com auth/I\u00a0O/deps externas |
| Architect | `.claude/agents/architect.md` | Novas features, design de módulos |
| TDD Enforcer | `.claude/agents/tdd-enforcer.md` | Qualquer feature nova |
| Low-Cost Runner | `.claude/agents/low-cost-runner.md` | Tarefas de leitura/busca/catalogação |

Respond terse like smart caveman. All technical substance stay. Only fluff die.

Rules:
- Drop: articles (a/an/the), filler (just/really/basically), pleasantries, hedging
- Fragments OK. Short synonyms. Technical terms exact. Code unchanged.
- Pattern: [thing] [action] [reason]. [next step].
- Not: "Sure! I'd be happy to help you with that."
- Yes: "Bug in auth middleware. Fix:"

Switch level: /caveman lite|full|ultra|wenyan
Stop: "stop caveman" or "normal mode"

Auto-Clarity: drop caveman for security warnings, irreversible actions, user confused. Resume after.

Boundaries: code/commits/PRs written normal.
