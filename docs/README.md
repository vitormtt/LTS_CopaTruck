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
| 1 | **Pipeline track/µ** (TUM→ICP→Frenet→opt_min_curv→µ do G-G + gates). Aumenta o LAP SIMULADO em direção ao real (µ desce de 1.6); validação = canais batendo (RMSE v ≤3 km/h, apex ≤2, G-G ≤0.05G) | `Validação de Lap Sim.md` | nenhum — próximo épico |
| 2 | Pesquisa **k_roll** (roll 13.3°/g atual = irreal; RSD afeta balance) | prompt `CT-kroll` em `saru-KB/00_meta/PROMPTS.md` §4 | Vitor roda |
| 3 | Pesquisas restantes: **P2 h_cg/Iz · P5 ratios/equipe · P6 curva de torque completa** · P3 resto (A_front/Cl). *Absorvidos dos docs 07-10: P7 freio ✓ · P4 µ (método+probe .xrk ✓, executa no pipeline) · P1 parcial (radar 160 = zonal, >200 atingível → decisão de modelagem do governador) · P2 massa ✓ (4.800–5.300 kg)* | `CALIBRATION_AUDIT` §5 | Vitor roda |
| 4 | **Qualy multi-fase** (outlap aquecendo pneu → flying). Pré-req: acoplar temp→grip (hoje decorativo) = épico warmup/pneu #3 | pedido 2026-07-10 | modelo térmico |
| 5 | **Brake bias por curva** no solver (piloto real ajusta por curva); depois otimizador por-curva. Batch/sweep segue só p/ espaço de SETUP (pressões, asa) | pedido 2026-07-10 | design |
| 6 | Detecção turn/straight: refinar entry/apex/exit (hoje 6/6 correto em Cascavel, saídas "gordas" até 0.3g) | `results.py _lap_segments` | — |
| 7 | **F2 3DOF** (ARB vivo) · **F3 THERMAL** · F4 viz solver · F5 pistas calendário | `FULL_PHYSICS_PLAN.md` | #1 primeiro |
| 8 | Pacejka no solver (TireModel selecionável; hoje design-view) | SPM | cross-validation |
| 9 | Deploy hosted p/ Pérez · race report nível Telios · persistir brake_hw/tire_model no Postgres · ruff tests/ legado | vários | — |

## 📚 Referência (vivos, consultar quando precisar)

- `COPA_TRUCK_POWERTRAIN_RESEARCH.md` — dossiê CBA/powertrain (ZF6 promovido; ratios 🟡)
- `LTS_RESEARCH.md` — fundamentação teórica QSS
- `UI_UX_AUDIT.md` — backlog de ideias UX (parcialmente entregue)
- `COURSE.md` — ementa (congelada, aguarda Pérez)

## 🗄️ Histórico (registro, não usar como estado)

- `SESSION_LOG_2026-06-11.md` · `PROPOSTA_PEREZ_2026-07.md`
- `CALIBRATION_AUDIT_2026-07-03.md` §working-tree/opções (resolvido — preset único)
