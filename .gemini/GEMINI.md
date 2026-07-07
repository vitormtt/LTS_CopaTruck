# LapTimeSimulator_CopaTruck

<!-- SARU-DOC-SYNC:START (gerado por saru-doc-sync.sh — NAO duplicar regras globais aqui) -->
> **Regras globais (operador):** `~/.claude/CLAUDE.md` — fonte unica (versao vigente no proprio arquivo). NAO duplicar aqui.
> **Memoria global SARU:** `/home/vitor/Projects/01_Workspace/SARU_GLOBAL_MEMORY.md`
> **Memoria deste repo:** `SPM.md`
> **Git Flow:** `main` (release) + `develop` (integracao) + `feature/*`. Merge `--no-ff`. Sem PR.
<!-- SARU-DOC-SYNC:END -->

> **SoT de arquitetura:** `docs/ARCHITECTURE.md` (estrutura, física, OOP, code standards).
> **Memoria/estado:** `SPM.md` · **Decisões:** `docs/` · **Engine:** Claude Code only.
> Este arquivo é lean — detalhe técnico vive em `docs/`.

## Context
- Lap time simulator for Copa Truck — SARU Dynamics product
- Technical partnership: Pérez (post-graduation)
- Stack: Python 3.x, Streamlit, NumPy, SciPy, HDF5, PostgreSQL
- GitHub: `vitormtt/LTS_CopaTruck`
- Local: `~/Projects/SARU/partnerships/lts-copatruck/`

### Hooks Automaticos de Memoria
- **Startup:** Ler `SPM.md` p/ contexto do repo.
- **Durante:** Atualizar `SPM.md` no mesmo turno que muda arquitetura/estado.
- **Stop/Handoff:** Consolidar `SPM.md`.

### AgentShield
- CLI/scripts: sempre dry-run/`--help` antes de delegar a Vitor.
- Scraping/credenciais/destrutivo: auditar vazamentos antes, isolar em dry-run.

## Golden Rules for Claude

1. **Never hardcode vehicle or track parameters** — all values via `VehicleParams` JSON or HDF5.
2. **Never alter the two-pass solver** without cross-validation against known lap times.
3. **pytest must pass 100%** before any commit is proposed.
4. **ABCs must be fully implemented** — no abstract method left unimplemented in subclasses.
5. **Keep docs in sync** — structural change → update `docs/ARCHITECTURE.md` + `SPM.md`.

## Status & Roadmap
Estado atual, pendências e roadmap vivem em `SPM.md` (§2). Pesquisa regulatória/powertrain em `docs/COPA_TRUCK_POWERTRAIN_RESEARCH.md`.
