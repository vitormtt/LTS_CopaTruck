# AGENTS.md — Memória Persistente Inter-Sessões

<!-- SARU-DOC-SYNC:START (gerado por saru-doc-sync.sh — NAO duplicar regras globais aqui) -->
> **Regras globais (operador):** `~/.claude/AGENTS.md (OpenCode)` — fonte unica (versao vigente no proprio arquivo). NAO duplicar aqui.
> **Memoria global SARU:** `/home/vitor/Projects/01_Workspace/SARU_GLOBAL_MEMORY.md`
> **Memoria deste repo:** `SARU_PROJECT_MEMORY.md`
> **Git Flow:** `main` (release) + `develop` (integracao) + `feature/*`. Merge `--no-ff`. Sem PR.
<!-- SARU-DOC-SYNC:END -->




> EXECUTOR: Motor C (OpenCode). Matriz: A=Claude Code, B=Antigravity, C=OpenCode.

> Padrão: claude-mem / Compound Learning
> **SEMPRE leia este arquivo no início de cada sessão.**
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

## Hooks Automáticos de Memória (Session & State)

**Startup:** Ler `~/Documents/Obsidian/00_SYSTEM/hot.md` silenciosamente p/ contexto vivo.

**Durante:** Qualquer decisao/correcao/mudanca de plano → atualizar `hot.md` (status), `LEARNINGS.md` (instintos), `.md` globais no mesmo turno. Nunca esperar Vitor pedir.

**Stop/Handoff:** Consolidar `hot.md` + `HANDOFF-PROXIMA-SESSAO.md` automaticamente.

---

## AgentShield (Seguranca & Sanity Check)

1. **NUNCA** delegar execucao cega de CLI/scripts a Vitor. Sempre dry-run/`--help` em background primeiro.
2. Scripts de scraping/credenciais/comandos destrutivos → agir como escudo: auditar codigo p/ vazamentos ANTES, isolar em dry-run.

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

---

## Subagent Routing (Auto-Dispatch)

| Trigger | Agent |
|---------|-------|
| novo repo/pasta, mapear | explorer |
| task afeta 3+ arquivos | planner |
| escrever/editar codigo | maker |
| rodar testes, validar | tester |
| package/env/secrets edit | auditor |
| docs, status.md, README | scribe |
| .m, .slx, MATLAB | matlab-expert |
| 90min sessao | adhd-coach |
| PostUserPrompt apos correcao | reflector |
| weekly OR padrao recorre 3x | promoter |
| MEMORY.md > 200 linhas | archivist |
| 3 sessoes repetem sequencia | skill-extractor |
| mensal cron | process-optimizer |
| Vitor diz "iniciar projeto novo" | inception-facilitator |
| pesquisa profunda, pdfs densos | notebooklm-specialist |
| limpeza legados | janitor |

---

## Startup SARU

```bash
ls ~/Projects/01_Workspace/ 2>/dev/null && \
  cat ~/Projects/01_Workspace/SARU_GLOBAL_MEMORY.md || \
  cat ~/.claude/context/saru_global_memory.md
```

Tambem ler: `<projeto>/SARU_PROJECT_MEMORY.md`

---

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
