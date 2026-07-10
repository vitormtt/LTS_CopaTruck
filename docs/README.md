# docs/ — Índice e Status

> Auditado 2026-07-10. Cada doc carrega banner de status no topo.
> Estado vivo do repo = `SPM.md` (raiz). Este índice responde: o que está
> FEITO e o que FALTA.

## ✅ Feito e consolidado (pode mudar com novas pesquisas/resultados)

| Doc | O que entrega |
|---|---|
| `Especificações Freio Copa Truck.md` | Pacote de freio researched (Knorr SN7 + PD/116) — **APLICADO** no preset/solver. Ref 17 quebrada → valores soft = estimados |
| `research/PROMPT_brake_hardware.md` | Prompt respondido (registro) |
| `research/PROMPT_track_reconstruction.md` | Prompt respondido (registro) |
| `research/RSD_Sonnino2026_roll_stiffness_synthesis.md` | Física de balanço validada; canal handling_balance feito |
| `FULL_PHYSICS_PLAN.md` §F1, §F3-hardware | Racing line always-on + width ✅ · freio Limpert ✅ |
| `ARCHITECTURE.md` | SoT técnico — atualizado 2026-07-10 (árvore + defaults físicos) |

## 🔜 A fazer (ordem de prioridade)

| # | Trabalho | Fonte/spec | Bloqueio |
|---|---|---|---|
| 1 | **Pipeline track/µ** (TUM→ICP→Frenet→opt_min_curv→µ do G-G + gates de validação) | `Validação de Lap Sim.md` | nenhum — próximo épico. Fecha o fudge µ=1.6 (−8.7s exposto) |
| 2 | Pesquisas abertas: **P4 µ pneu · P1 governador · P2 massa/CG/Iz · P5 ratios/equipe · P6 curvas torque** · P3 resto (A_front/Cl) | `CALIBRATION_AUDIT_2026-07-03.md` §5 | Vitor roda (Gemini/Perplexity) |
| 3 | **F2 3DOF** (ARB vivo) · **F3 THERMAL** (fade validado) · F4 viz solver · F5 pistas calendário | `FULL_PHYSICS_PLAN.md` | #1 primeiro (µ recalibrado) |
| 4 | Pacejka no solver (TireModel selecionável; hoje é design-view) | SPM §0 p2 | cross-validation |
| 5 | Deploy hosted p/ Pérez (VPS + auth) | `DISTRIBUTION_OPTIONS.md` | decisão de timing |
| 6 | Race report nível Telios (pressão/temp por canto/volta) | `Telios_prints_transcricao.md` | — |
| 7 | k_roll com fonte (roll 18.8° indicativo) · persistir brake_hw/tire_model no schema Postgres · ruff tests/ legado | SPM | — |

## 📚 Referência (vivos, consultar quando precisar)

- `COPA_TRUCK_POWERTRAIN_RESEARCH.md` — dossiê CBA/powertrain (ZF6 promovido; ratios 🟡)
- `LTS_RESEARCH.md` — fundamentação teórica QSS
- `UI_UX_AUDIT.md` — backlog de ideias UX (parcialmente entregue)
- `COURSE.md` — ementa (congelada, aguarda Pérez)

## 🗄️ Histórico (registro, não usar como estado)

- `SESSION_LOG_2026-06-11.md` · `PROPOSTA_PEREZ_2026-07.md`
- `CALIBRATION_AUDIT_2026-07-03.md` §working-tree/opções (resolvido — preset único)
