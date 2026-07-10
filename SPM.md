# SARU Project Memory — LapTimeSimulator_CopaTruck

> Última atualização: 2026-07-10
> LER ao iniciar. ATUALIZAR ao final de cada tarefa.

---

## 0. Sessão 2026-07-10 (parte 4) — racing line ALWAYS-ON + width + auditoria docs

- **RACING LINE SEMPRE É O DRIVING PATH (`00eb870`, diretiva Vitor)**: `use_racing_line`
  default True (dataclass + dict path); toggle da Track page virou **viz-only**
  ("Show racing line on map"). False só como baseline de debug centerline.
- **CORREDOR POR LARGURA DE VEÍCULO (doc Validação mandava)**: `compute_racing_line`
  ganhou `vehicle_width_m` — bounds do QP viram ±(1−margin), margin=(w/2)/half_width
  clip 0.95. Largura = bitola + 1 seção de pneu (`_TYRE_SECTION_WIDTH_M=0.295`).
  Caminhão 2.4m ≠ fórmula. **Cache do solver keyed por largura** (trocar veículo
  recomputa). Viz da Track usa a MESMA largura (vp salvo) — mapa bate com solver.
- **Δ (µ=1.6 held)**: Cascavel qualy 75.57→**70.78s** (−8.7s vs real 79.505 — fudge µ
  TOTALMENTE exposto, todos os componentes estruturais agora honestos). Interlagos
  **121.36s** vs real 123.9 (racing line absorveu o grosso do ruído da centerline!).
  Baselines regeneradas; asserts 69–74 / 118–126 + bias threshold 0.03→0.02 (traçado
  suave freia menos) com rationale. **206 verdes.**
- **AUDITORIA DE DOCS FEITA (`d8aae17`, pedido Vitor)**: TODOS os 16 docs ganharam
  banner de status (✅ aplicado / ⚠️ parcialmente superseded / referência / histórico /
  prompt respondido). **`docs/README.md` = índice mestre** (feito vs a-fazer priorizado
  vs referência vs histórico). ARCHITECTURE atualizado (árvore real + defaults físicos
  2026-07-10). FULL_PHYSICS: F1 ✅, F3-hardware ✅. CALIBRATION_AUDIT: P7+track
  respondidos; **P4 µ, P1 governador, P2 massa/CG/Iz, P5 ratios, P6 torque = ABERTOS**.
- **PRÓXIMO ÉPICO CRAVADO**: pipeline track/µ (doc Validação) — recalibra µ com gates
  formais (RMSE ≤3 km/h, apex ≤2, G-G ≤0.05G, sim 0.5–2% mais rápido). Fecha o −8.7s.

## 0. Sessão 2026-07-10 (parte 3) — FUSÃO DE PRESETS + qualy flying + results rework

- **FUSÃO DE PRESETS (`40cf6f5`, DECISÃO VITOR "confirmo fusão")**: preset único
  **`volkswagen_31320` = "VW 31320 (Copa Truck)"** com a física researched (ZF6 6M 3.42,
  r_wheel 0.52, Cx 0.74, driveline 0.88, abs OFF, brake_hw 314/263). `vw_31320_zf6_reference`
  **DELETADO** (motivo: nunca mais rodar modelo stale por engano). Testes que referenciavam o
  experimental re-apontados.
- **QUALY = FLYING LAP por default (`40cf6f5`, fix do "sai a 40 km/h" — 2ª reclamação)**:
  `use_flying_lap_start` default True (dataclass + dict path solver:1584). Qualy agora larga
  a **v0≈180 km/h** (BC periódica). Standing start intacto (80.46s).
  **Δ Cascavel qualy: 80.69 → 75.57s** — overshoot -3.9s vs pole real 79.505 = **µ=1.6 fudge
  EXPOSTO** (era co-calibrado com launch frio). Recalibração µ = épico pipeline (próximo).
  Baselines regeneradas + assert range 74–78 com rationale (âncora real vive aqui no SPM como
  alvo de CALIBRAÇÃO, não de regressão). Interlagos qualy 132.7 (centerline ruidoso conhecido).
- **RESULTS REWORK (`81daa49`, batch 6 itens Vitor)**: (1) qualy 40 km/h ✅ acima. (2) **roll
  derivado** quasi-static φ=m·ay·h_cg/k_roll (KPI 18.8° no lap — magnitude indicativa, k_roll
  230k SEM FONTE, caption avisa; era sempre 0 pois solver nunca exportou o canal). (3) history
  movido pro fim. (4) resposta rear-lock: transferência de carga alivia traseira + bias 60% <
  neutro (~65-70% ótimo) → rear satura primeiro; físico, não bug. (5) axis titles com unidade
  em TODOS os plots. (6) **setores: slider removido** → 3 setores fixos + breakdown expansível
  curva/reta por setor (detecção |a_lat|>0.3g, blips <30m fundidos; Cascavel detecta 8 curvas ✓)
  com tempos/share/v/peak-G.
- **Verificado live**: preset único, lap 1:15.571 (bate headless), roll não-zero, slider fora,
  3 breakdowns + history no fim, zero exceptions. **205 passed.** Fix no caminho: `mass_geometry.
  cg_height` (não h_cg) — AttributeError pego no preview.
- **⚠️ ESTADO DE CALIBRAÇÃO**: física estruturalmente honesta (flying, ZF6, freio hardware,
  no-ABS) mas **µ=1.6 segue fudge** → sim -4.9% vs real. Gate alvo pós-pipeline: 0.5-2% mais
  rápido que piloto real (doc Validação). NÃO retunar µ na mão — esperar pipeline track.

## 0. Sessão 2026-07-10 (parte 2) — research freio APLICADA + design views UI

- **RESEARCH CHEGOU (2 docs no `docs/`)**: `Especificações Freio Copa Truck.md` (responde
  PROMPT_brake_hardware: Knorr SN7 2×68mm, câmaras Tipo 24/20 → pressão hidráulica equivalente
  **314/263 bar** F/R, Fras-le PD/116 µ **0.48**, disco 430mm → R efetivo **0.1725 m**; teto
  hardware ~5.45g >> grip ⇒ freio é grip-limited; validação telemetria 0.8g sustentado /1.4g pico)
  + `Validação de Lap Sim.md` (responde PROMPT_track_reconstruction: pipeline TUM→ICP/Procrustes→
  Frenet→opt_min_curv→µ do G-G; **gates**: RMSE ≤3 km/h, apex ≤1.5-2 km/h, microssetor ≤0.15s,
  G-G ≤0.05G, sim 0.5-2% mais rápido que piloto real). ⚠️ Ref 17 do doc freio = unknown_url →
  valores soft (alavancagem 15.6, 314/263, 0.48, 0.1725) tratados como ESTIMADO.
- **WIRING FREIO FEITO (`1b33bd2`)**: `brake_hardware.py` +`wheels_per_axle=2` (doc conta 1 caliper/
  roda; módulo somava 1/eixo — teto agora 5.50g, bate doc); `BrakeParams.hardware_front/rear`
  opcionais → `VehicleParams.derived_brake_force()` → override de `max_brake_force` no to_solver_dict
  (fallback slider quando None) + roundtrip + validação; preset experimental ganhou blocos
  `brake_hw_front/rear`. **Δlap experimental = +0.0000s** (80.009, grip-limited como doc previu),
  default byte-intacto (80.694). Bias natural pneumático **54.4% front**. Nota: caminho Postgres
  (vehicle_mapping) NÃO persiste hardware (só JSON fallback) — aceitável V1.
- **DESIGN VIEWS UI (`2c13e51`, pedido 3-itens do Vitor)**: (1) **Tires**: radio Linear|Pacejka
  (persistido `TireParams.tire_model`, roundtrip OK); branch Pacejka edita B/C/D/E + plota **Fx, Fy,
  Mz, Mx, My** do novo `src/vehicle/tire_model.py` (MF puro; ratios de forma da literatura como
  constantes nomeadas; slider Fz ref default = quarter static). Solver SEGUE linear (rotulado na UI;
  wiring Pacejka no solver = mudança guardrail futura). (2) **Transmission**: `transmission_curves.py`
  puro → plots V-por-marcha vs RPM + força trativa sawtooth vs road load (arrasto+rolagem) —
  valida gearing visualmente. (3) **Brakes**: toggle hardware **editável em QUALQUER preset**
  (default OFF; liga → 6 inputs seeded com pacote researched, metric força derivada + bias natural,
  input manual disabled). Verificado live: default r_wheel 0.65 → 213.5 kN (=266.9×0.52/0.65,
  consistente). **205 passed, 2 skipped**; ruff limpo.
- **Follow-ups**: (a) épico pipeline track/µ (doc Validação §Pipeline: TUM+ICP+Frenet+gates) =
  PRÓXIMA GRANDE TAREFA, desbloqueada; (b) Pacejka no solver (cross-validation); (c) persistir
  hardware/tire_model no schema Postgres; (d) ruff tests/ legado 26 findings.

## 0. Sessão 2026-07-10 — ruff cleanup + viz lockup/balance (V1+V2) FEITA

- **RUFF CLEANUP COMPLETO** (pendência #6/§0-2026-07-08): 41 findings → **0** (`ruff check src/`
  All checks passed). Commit `1c42cee`. Inclui **fix de bug latente**: `tracks/visualize.py` usava
  `CircuitHDF5Reader` sem import (F821 → NameError se rodado). Removidos 19 imports mortos + 3 locals
  mortos (`lon0`/`mode`/`ambient_temp_c`), `__all__` no barrel `components/`, E402 scoped via
  `per-file-ignores` (entry points bootstrap sys.path — legítimo). Verificado: smoke-import de todos
  os módulos tocados OK (`libxrk` falha = dep opcional pré-existente, não-relacionado).
- **VIZ #10/balance FEITA (V1+V2, commit `8466213`, decisão Vitor "V1+V2 completo")** — resolve a
  pendência #1 de viz (canais exportavam CSV, faltava plot). Arquitetura: helper **puro**
  `src/analysis/driver_report.py` (`driver_report_from_result(res, params)` → lockup+balance channels
  + KPIs, zero streamlit, 4 testes) reusado por DOIS consumidores:
  - **Aba "Balance & lockup"** no `results.py` (5ª tab): 4 KPIs (peak front/rear margin, near-lockup %,
    mean balance±tendency) + 2 plots (margem travamento F/R vs dist + linha ref 1.0; balanço assinado
    understeer/oversteer). Cor semântica (theme tokens).
  - **Seção "Handling & Brake Balance"** no PDF (`generate_pdf_report` ganhou param `params` opcional).
  - **VERIFICADO LIVE no preview** (streamlit 8501, viewport 1440×900 — nota: viewport 0×0 colapsa a
    sidebar do Streamlit, setar tamanho antes): sim default Cascavel 1:20.695, aba renderiza sem erro,
    **rear = eixo limitante (margem 0.98 vs front 0.12), near-lock 38%, balance −0.001** (quase neutro).
    PDF button presente sem exception. Screenshot deu timeout (15 plots pesam o renderer) — prova via DOM.
- **Suíte: 188 passed, 2 skipped** (183 + 4 driver_report + 1). `develop` sincronizado com origin
  (`1c42cee`→`8466213`).
- **Pendências restantes** (todas bloqueadas em pesquisa Vitor, ele avisa quando voltar): calibração µ,
  P1–P7 (`CALIBRATION_AUDIT §5`), recaptura Interlagos (TUM FTM), wiring `brake_hardware.py`. Prompts
  priorizados entregues ao Vitor: track_reconstruction (keystone) > P4 µ > P1 governador > P6 torque >
  P2 massa/CG > P5 transmissão > P7/brake_hardware. P3 aero quase resolvido (Cx 0.74), ARB pelo paper RSD.

## 0. Sessão 2026-07-08 — consolidação develop + lint gate restaurado

- **`develop` CONSOLIDADO e pushado** (`origin/develop` = local, sincronizado). Push dos 8 commits
  da sessão parte-3 (`af84c06..b5978b9`: pressão car→truck, preset ZF6, #10 V1/V2 lockup, paper RSD,
  balance channel) + 1 commit de tooling. **183 passed, 2 skipped** confirmado (re-rodado, 10s).
- **LINT GATE RESTAURADO** (pendência §0 parte-3 #6): `ruff>=0.6` + `mypy>=1.11` adicionados ao
  `[dependency-groups] dev` do `pyproject.toml` + config mínima (`line-length=100`, `target py310`,
  `ignore_missing_imports`). `uv sync` instalou (ruff 0.15.20, mypy 2.2.0). Commit `6a864cf`
  `chore(deps): add ruff and mypy to dev toolchain` (gitleaks limpo). **`/lint-and-validate` volta
  a funcionar local.** ⚠️ `ruff check src/` → **41 findings** (19 auto-fixáveis: imports não usados
  etc.) — cleanup é **tarefa separada** (toca ≥3 arquivos, precisa OK). Gate está VIVO, código não limpo ainda.
- **AGENTS.md — nota STALE CORRIGIDA**: handoff/SPM diziam "typechange pendente no working tree".
  FALSO agora — `git` limpo, AGENTS.md commitado como **arquivo real tracked** (mode 100644, commit
  `34de1bb` "tracked mirror") **idêntico** a CLAUDE.md (39 linhas, `diff -q` = igual). Inócuo (não há
  pendência). Nota: regra global pede symlink, mas commit fez mirror real deliberado — conflito de
  intenção não-resolvido, mas SEM efeito enquanto idênticos. Não mexido (baixo valor, risco de churn).
- **Pendências que sobram** (nada bloqueia consolidação): (1) viz Streamlit dos canais lockup +
  handling_balance (#10 V1 + balance exportam CSV, falta plot — não-verificável headless). (2) ruff
  41-findings cleanup. (3) bloqueadas em pesquisa Vitor: calibração µ, recaptura Interlagos (TUM FTM),
  wiring `brake_hardware.py`, sourcing sens pressão/µ. (4) AGENTS.md symlink-vs-mirror (cosmético).

## 0. Sessão 2026-07-07 (parte 3) — Batch B física: preset experimental (AGUARDA OK VITOR)

- **Preset experimental `vw_31320_zf6_reference` CRIADO** em `data/vehicle_models.json`
  (isolado, default `volkswagen_31320` byte-idêntico, **162 testes verdes**). NÃO commitado —
  guardrail: aguarda OK do Vitor. **µ HELD 1.6** (não tocado, SPM §0b). Valores:
  ZF6M `[6.75,3.60,2.13,1.39,1.00,0.78]` n_gears=6, final_drive 3.42, r_wheel 0.52,
  driveline_eff 0.88, abs_enabled False, **Cx 0.74** (data-matched, NÃO 0.85 do research).
- **Resultado (real load path, µ=1.6)**: Cascavel **79.965s / vmax 186.9 km/h** vs real
  79.505 / 186.6 (**Δ+0.46s / +0.3 km/h** — bate lap E topo). Bate o default (80.694 / 192.3 =
  +1.19s / +5.7). Interlagos 133.351 / 194.0 (centerline ruidoso = blocker conhecido, +9.5s).
- **ACHADO — Cx research 0.85 é DRAGGY demais**: overlay vs .xrk (cached `src/results/test_converted*.csv`,
  sem libxrk no venv) → real Cascavel vmax **186.6**, Interlagos real bate governador **199.6**
  mas exp@Cx0.85 capa em 188 (regressão). Sweep Cx → **0.74** reproduz Cascavel real vmax (186.9).
  .xrk > estimativa genérica bluff-body (crítica: 2 fontes conflitam, dado real ganha).
- **ACHADO — modelo de pressão do `setup.py` é ESCALA DE CARRO e está VIVO** (não gated como o
  bloco térmico do `_axle_grip`): `_TYRE_PRESSURE_REFERENCE=1.8 bar`, clip `[1.4, 2.4]`,
  `_MU_CHANGE_PER_BAR=-0.03` (Porsche Carrera Cup src). `run_bicycle_model:1552` propaga
  `P_cold_bar`→`setup.tyre_pressure` com clip. Setar P_cold_bar truck-scale (7.58 bar) → clipa
  a 2.4 → penalidade espúria de grip (−1.8% mu, +0.38s). **`P_cold_*_psi` são INERTES** (só
  `P_cold_bar` conta). ⇒ pressão de caminhão (110 psi) = **rework GLOBAL do setup.py**
  (min/max/ref/sens), afeta default → tarefa separada + OK. Preset deixou pressão default.
- **abs_enabled False** = fator plano `_NO_ABS_MODULATION=0.94` no brake cap (grip-limited,
  +0.04s). Com abs=True + abs_slip_target=0.15=_ABS_PEAK_SLIP → fator 1.0. **#10 real** = modelo
  de slip ratio/lockup (KB §10: sx=(ωR−vx)/vx), NÃO feito ainda — é código novo no solver.
- **Cx 0.74 CONFIRMADO pelo Vitor** (entendeu que Cx=arrasto aero, não pneu). Preset fica 0.74.
- **REWORK DE PRESSÃO FEITO (car→truck) — PHYSICS-NEUTRO, 162 verde**: `setup.py` ref
  1.8→7.58 bar (110 psi), clip [1.4,2.4]→[6.55,8.62] (95–125 psi), sens `_MU_CHANGE_PER_BAR`
  −0.03→−0.0145 / `_CS_CHANGE_PER_BAR` 0.15→0.072 (rescaladas p/ banda larga, interim s/ fonte).
  Default `VehicleSetup`/`get_default_setup`/`TireParams`/fallbacks → 7.58/110. `optimization.py`
  janela 6.55–8.62 + reset a 7.58 (ref=neutro). UI `vehicle_params.py` slider 95–125 psi. Ambos
  presets JSON → P_cold_bar 7.58 / psi 110. **PROVA de neutralidade**: `git diff regression_baselines.json`
  = SÓ `final_tyre_pressure_bar` mudou (2.3→8.1 bar, +5.78 = delta cold); lap/v/rpm/gear/temp/fuel
  byte-idênticos. Baselines regeneradas legitimamente (só canal de pressão). Default Cascavel
  80.694/192.3 intacto. **COMMIT `ac130b2`** (refactor pressure). Preset Part B = commit seguinte.
- **#10 lockup — ACHADO**: `_bias_limited_decel` (solver:512) JÁ é modelo Limpert de primeiro-eixo-
  travando com transferência de carga → **bias JÁ é funcional** no cap. Logo #10 NÃO é "adicionar
  lockup" (existe); é lado-piloto: (V1) canal de telemetria de margem de travamento por eixo
  (mostra risco por curva, driver-training, ZERO mudança de lap = derived) vs (V2) driver-error
  model que de fato trava e perde tempo (épico "driver frontier", + wiring `brake_hardware.py`
  bloqueado em números reais). Fork de escopo aguarda decisão Vitor.
- **DECISÃO VITOR**: commitar ambos + implementar #10 **V1 + V2** ("3+1+2"). TUDO FEITO.
- **4 COMMITS na develop (173 verde, sem push)**: `ac130b2` refactor pressão · `575fd35` feat
  preset ZF6 · `f32ace3` feat #10 V1 lockup channel · `cd537c3` feat #10 V2 bias-aware no-ABS.
- **#10 V1 FEITO (`f32ace3`)**: `src/analysis/brake_lockup.py` puro — margem de travamento por
  eixo (Limpert first-lock + transferência + downforce) + slip est (KB §10). Wired em
  `SimulationTelemetry(result, params=...)` → canais CSV `brake_lockup_front/rear/slip`. DERIVED,
  zero solver, lap intacto. 9 testes. Experimental@60% bias: **rear é o eixo limitante**
  (margem 0.92 vs front 0.12) = confirma bias rearward. Falta só: plot na Results UI (surfacing).
- **#10 V2 FEITO (`cd537c3`)**: `_brake_system_cap` no-ABS modulation agora **bias-aware** via
  `_axle_lock_balance` (0.88 imbalanced → 0.97 balanced; era flat 0.94). SÓ afeta abs=False.
  **Default (abs=True) BYTE-IDÊNTICO 80.694** (regression baselines intactos, cross-val golden
  rule #2). Experimental 79.965→80.009 (+0.044s, <0.5s). **BIAS AGORA FUNCIONAL**: sweep 55–78%
  front = 0.14s, ótimo ~65–70% (60% era rearward-imbalanced). Teste bias-functional. Ponto-massa
  limita magnitude (freio move pouco), mas bias deixou de ser inerte.
- **PENDÊNCIAS**: (1) plot lockup na Results UI (V1 já exporta p/ CSV; falta viz Streamlit —
  não verificável headless aqui). (2) V2+: driver-error estocástico (trava DE FATO com erro) =
  épico "driver frontier" maior. (3) wiring `brake_hardware.py` bloqueado em números reais
  (`PROMPT_brake_hardware.md`). (4) pressão sens + µ = interim s/ fonte. (5) recaptura Interlagos
  segue pré-req da calibração µ (§0b). (6) venv sem ruff/mypy (gate de lint local quebrado).

### Paper Sonnino 2026 (RSD / roll stiffness) — VALIDA nossa física
- **Artigo** (Vitor mandou, "muito importante"): Sonnino et al., *Active control of vehicle lateral
  dynamics through roll stiffness distribution*, Control Eng. Practice 168 (2026) 106735 (PoliMi+Brembo).
  PDF em `docs/research/` (gitignored). Síntese umbrella em
  `docs/research/RSD_Sonnino2026_roll_stiffness_synthesis.md` (commitada).
- **ACHADO**: nosso solver JÁ implementa a Eq (3) do paper (split de transferência lateral por RSD):
  `lap_time_solver.py:680` `dfz_f = m·a_lat·h_cg/tw_f · frac_f`, `frac_f = k_roll_f/(k_roll_f+k_roll_r)` = RSD.
  Direção under/oversteer bate (↑front RSD → ls_f↓ → understeer). **Física de balanço CONFIRMADA, sem bug.**
- **RESOLVE o "ARB inerte"** com fonte citável: ganho steady-state é PEQUENO (+7.6% ay lateral mesmo
  com AARB ativo +50%); valor do ARB é TRANSIENTE (yaw settling −72%, sine-dwell overshoot −71%) →
  exige 3DOF+/14DOF (saru-core), não é patch de QSS. ARB chapado no nosso lap é CORRETO, não gap.
- **Umbrella**: lts-copatruck física OK (só falta canal telemetria de balanço under/oversteer, padrão
  derived tipo brake_lockup); saru-core = onde ARB rende (14DOF + controle FF λ + FB yaw-rate + LQR ARS);
  saru-os = harness ISO 4138/7401/19365 + KPIs; driver-model = yaw-rate ref (Eq 7-9) como alvo.
- LapLabs.net = produto de telemetria/ML sim-racing (iRacing), NÃO fonte de física. Benchmark de UX
  p/ overlay/race-report só.
- **FEITO (commit seguinte ao doc)**: canal de telemetria `handling_balance` (`src/analysis/handling_balance.py`)
  — utilização de grip por eixo (demand/capacity) + balanço assinado (>0 understeer). Derived, ZERO
  solver, wired em SimulationTelemetry (`balance_front_util/rear_util/handling_balance`). **Torna ARB
  VISÍVEL**: front-stiff→understeer (+0.031), rear-stiff→oversteer (−0.033), lap idêntico 80.009 nos 3
  (confirma paper: RSD não move lap QSS). 9 testes. Total suíte **183 verde**. É a oportunidade #1 do
  synthesis doc. Restam: #3 harness ISO (saru-os), #2 yaw-ref transiente (muda solver), plot Streamlit.
- **7 COMMITS totais na sessão** (develop, sem push): ac130b2 pressão · 575fd35 preset ZF6 · f32ace3
  #10 V1 lockup · cd537c3 #10 V2 bias-aware · c7afefb docs paper RSD · +balance channel · +este SPM.

## 0. Sessão 2026-07-07 (parte 2) — consolidação develop + auditoria física

- **`develop` CONSOLIDADO e pushado** (`origin/develop` = local, 0/0, **162 testes verdes**).
  Merge `--no-ff` de `feature/claude-product-upgrade` (`d2249be`) — traz Batch A viz + Race
  Report + racing line + flying-lap flag; junto do trabalho da VM Cowork (transcrição Telios
  real + `scripts/transcrever_telios.py`). Batch A saiu de "uncommitted" (§0b) para MERGED.
- **Infra**: `pytest` declarado em `[dependency-groups] dev` (`7acc7e8`) — fix do bug em que
  `uv sync` removia pytest e quebrava a suíte. **`.gemini/` untracked** (`f11cc3e`, git rm
  --cached + gitignore) alinhando claude-only (regra global zero-GEMINI); preservado no disco.
  Imagens `docs/Telios imagens/` gitignored (5 MB; transcrição textual é a fonte versionada).
- **VM Cowork**: matar qemu+virtiofsd NÃO segura — `cowork-svc-linux`/`cowork-linux-helper`
  (filhos do Claude Desktop) relançam a VM. Helper sozinho (sem qemu) é inócuo. Fechar de vez
  = pela UI do Desktop. Guard de VM real: `ps -eo comm= | grep -qx qemu-system-x86`
  (`pgrep -f "...cowork"` se auto-matcheia = falso positivo).
- **AUDITORIA FÍSICA** (docs Drive `copa_truck_architecture_design.md` + saru-KB + dossiê CBA) —
  confirma e amplia §0b. Alvos do preset experimental `*_zf6_reference` (guardrail, não mexer
  default sem OK): caixa **12M → ZF 6S 6M** `6.75/3.60/2.13/1.39/1.00/0.78` diff 3.42 (causa
  raiz #9); **r_wheel 0.65 → 0.52** (295/80 R22.5); **`abs_enabled=True` é FAKE** (Copa Truck
  sem ABS → item #10 lockup); `driveline_eff 0.95 → 0.88`; `Cx 0.7 → 0.85`; pressão UI
  20–34 psi → **95–125 psi**. Órfãos UI: `pacejka_E` exposto mas nunca usado no solver;
  `aero_balance`/`abs_enabled` vivos mas invisíveis; linha "Optimum 95 °C" decorativa (temp
  não acopla no grip). Telios = template do race report nível-pro (47 plots; pressão/temp por
  canto por volta = viz do warmup do #3).
- **Pendências**: `AGENTS.md` virou arquivo real (era symlink→CLAUDE.md) — typechange no
  working tree, não resolvido (baixo risco). Recaptura Interlagos segue pré-req da calibração (§0b).

## 0b. Sessão 2026-07-06 (parte 3) — triagem 13 itens produto + Batch A viz

- **Triagem completa dos 13 pontos do Vitor** (diagnóstico c/ evidência rodada). Ordem
  aprovada: (A) viz sign-fix → (B) física guardrail → (C) épico warmup/pneu → (D) setores-curva.
- **Batch A APLICADO (uncommitted, 164 testes verdes)** — zero guardrail (lap idêntico 80.69):
  - **#4/#8** `a_lat` do output agora **assinado** por `sign(kappa)` (`lap_time_solver.py`
    `_AY_SIGN=1.0`, +=esquerda). GG bilateral; casa .xrk (corr ay×v·yaw **+0.93**). Magnitude/
    lap intactos. Baseline regressão: só `ay_lat_g` atualizado (guard provou resto byte-idêntico;
    Interlagos pico lateral = curva à direita → vira `min`).
  - **#5** marcha em **eixo secundário** step (fim do `gear×1000` no eixo de RPM) — `results.py`.
  - **#6** gráficos agrupados em `st.tabs` [Track&dynamics / Brake&fuel / Chassis&driver /
    Sectors]. Lib p/ workspace arrastável real (futuro) = `streamlit-elements`.
  - **#11** overlay sim no race report agora bilateral (mesma raiz #4). Erro exato pendente Vitor.
  - **#12** já existia (radio Grid/DE). **#13** ARB precisa 3DOF (Fase 2).
- **⚠️ Possível sessão paralela**: porta 8501 ocupada por server de OUTRO chat neste repo.
  Não competi por porta (regra 1-sessão-por-repo). Verificar antes de continuar escritas.
### Batch B (física) — measure-first mudou o diagnóstico
- **#2 qualy v0**: bug real (hardcode `v0=10`=36 km/h). Fix = **BC periódica de flying lap**
  (`use_flying_lap_start`, default OFF, igual `use_racing_line`). Ligado: Cascavel 80.69→76.16.
- **#9 quedas em reta**: **NÃO é bug**. Cascavel+Interlagos: 1 dip ínfimo/volta; upshifts têm Δv
  POSITIVO. Powertrain/gearing OK. Zero mudança de código.
- **#1 freio**: sliders funcionam fraco (bias 40→70%=0.2s; force/decel saturam no default). O
  "não funcional" real = `brake_hardware.py` unwired + bias só importa com modelo de **travamento**
  = dobra no **#10** (Batch C). Ponto-massa grip-limited: freio quase não move lap (correto).

### CALIBRAÇÃO P0b — findado o nó (decisão Vitor: SEGURA)
- Recalibrei µ vs âncora Cascavel COM flying-lap+racing line ON, validando **traço** vs .xrk real
  (FG04 Superpole 79.96s). **Dados escolheram racing line** (RMSE 8.9 vs 13.9 km/h; µ físico).
- **µ = 1.165** (era **1.6** = ficção) → Cascavel flying+racing **79.50s** ✓ (âncora), traço RMSE
  8.9 km/h, vmax +4 (aero, follow-up). MAS **Interlagos = 136s** vs real 124.7 (**+11s**).
- **Nó**: 1 µ físico não bate as 2 pistas. Interlagos "quer" µ=1.6 = fiction compensando o
  **centerline ruidoso** (SPM: bloqueado). µ é do pneu (~1.15-1.3), não da pista → µ=1.165 correto.
- **DECISÃO VITOR (2026-07-06)**: **SEGURA a recalibração** até **recapturar centerline do
  Interlagos** dos GPS dos .xrk (`GPS Latitude/Longitude` presentes; reusar `generate_from_xrk.py`).
  Aí as 2 pistas ancoram juntas com µ físico. µ fica 1.6, flags default-off por enquanto.
- **Próximo**: recaptura Interlagos (ENU + spline periódica + boundaries) → re-rodar calibração.

### Recaptura Interlagos — GPS probe → decisão TUM FTM (2026-07-06)
- **Probe GPS (Andre Marques lap 1)**: extraí loop via `channels['GPS Latitude/Longitude']`
  (timecodes próprios, 25 Hz; `extract_session`/merge quebra nesse .xrk — usar canal cru).
  Loop 4241 m, fecha 0.6 m, Rmin ~25 m (0 pts <15 m = limpo). Com ele, **µ=1.165 (Cascavel)
  ancora as 2 pistas**: Interlagos 122.3 (racing ON) / 124.85 (racing OFF) vs real 124.7 —
  destravou o nó (era +11s). Provou que o centerline VELHO era o culpado.
- **DECISÃO VITOR**: GPS de 1 volta = racing line encolhida + ruído, **não condiz com real**.
  Segurar; **pesquisar metodologia** de reconstrução/validação (prompt em
  `docs/research/PROMPT_track_reconstruction.md`, Vitor roda no Gemini/Perplexity).
- **ACHADO forte**: repo já tem `TUMFTMDownloader` — `interlagos`→`SaoPaulo.csv` = **centerline
  SURVEYED + larguras reais por ponto** (862 pts, **4300 m** vs real 4309, bbox 666×1048 ≈ real).
  Download OK (testado). É a geometria de referência (mesma base do min-curvature TUM já no repo).
- **Plano pós-pesquisa**: geometria = TUM FTM (+ OSM fallback); GPS multi-volta (Interlagos 5,
  Cascavel 13) só p/ validar traço; alinhar frames (Procrustes/ICP por arc-length); µ calibra
  contra lap+traço. Provável recapturar Cascavel igual (centerline atual dá 85s racing-off, infiel).
- **Estado**: NADA aplicado. µ=1.6, flags default-off, tracks originais intactos. `interlagos_gps.hdf5`
  probe removido. Aguarda pesquisa do Vitor → então implementa pipeline TUM+validação.

### HANDOFF 2026-07-06 (Vitor abriu OUTRA sessão — driver model) — DIREÇÃO p/ próxima sessão
> ⚠️ **PARALLEL SESSION**: Vitor iniciou 2ª sessão neste repo (driver model). Regra 1-sessão/repo:
> ESTA sessão parou de escrever após este handoff. Coordenar antes de editar em paralelo.
- **Direção do Vitor (4 pontos) p/ a calibração de pista/µ**:
  1. **Âncora = tempos da INTERNET por pista** (records/pole oficiais), não só o .xrk. Cascavel
     79.505, Interlagos pole ~123.9. Levantar a tabela de tempos reais por pista do calendário.
  2. **Usar arquivos de REGULAMENTO por pista** p/ entender situações/limites de corrida (speed
     limit, pit, safety car, específicos do round). HOJE só existe `copa-truck-regulamento-tecnico-2025-.pdf`
     (geral) + `regulation_validator.py` (veículo). **Falta**: regulamento suplementar por pista → localizar/criar.
  3. **µ por pista CALCULADO do dado real TRATADO**, não back-fit de lap-time. Método: µ_tyre a partir
     do pico de |ay| medido no .xrk, corrigido por aero/transferência. **PROBE FEITO**: Cascavel real
     |ay| p95=1.06G p99=1.22G peak=1.38G → **confirma µ≈1.15-1.2** (bate com o 1.165 do lap-time). Este
     é o cross-check que valida a calibração — fazer igual p/ Interlagos.
  4. **DRIVER MODEL** (preocupação do Vitor "ta alucinando?"): hoje NÃO há driver model adaptativo —
     é QSS "piloto perfeito" no limite de grip (`_driver_inputs_from_accel`: throttle binário, brake do
     decel; segue centerline ou racing line min-curvature). Não alucina, mas é idealizado. Os GAPS do
     driver model = #10 (travamento/slip → piloto tem que modular sem ABS), racing-line realista, e a
     adaptação de linha ao setup. É a próxima fronteira (a 2ª sessão do Vitor).
- **Pipeline alvo (pós-pesquisa)**: geometria TUM FTM `SaoPaulo.csv` (surveyed, 4300m, larguras reais) →
  alinhar GPS multi-volta por arc-length (Procrustes/ICP) → boundaries reais → racing line TUM →
  µ do dado real (ponto 3) + validar traço RMSE vs .xrk + âncora tempos internet (ponto 1).
- **Commits desta sessão**: `d6e5818` (viz sign-fix Batch A) · `7ee53fc` (flag flying-lap) ·
  `789af02` (prompt pesquisa + achados). Suíte 164 verde no último estado tocado.

## 0. Sessão 2026-07-05 — branch `feature/claude-product-upgrade`

- Working tree pré-sessão estava LIMPO vs HEAD (contaminação GT de 2026-07-02 já
  descartada em algum momento; opção A da auditoria efetivada de facto). Asserts
  Cascavel 76–82 s vigentes; h_cg 1.1 nos presets.
- **Commits na branch**:
  - `feat(params): parameterize regulation speed governor` — `speed_limit_kmh` em
    `VehicleParams` (0.0 = fallback legado: Truck→200 km/h, resto ilimitado);
    `_build_flat_params` respeita override. 6 testes novos.
  - `feat(analysis): add sim-vs-reference telemetry overlay page` — `src/analysis/overlay.py`
    (puro: resample grade comum 5 m, Δv, Δt cumulativo, RMSE) + página Streamlit
    "Telemetry Overlay" (upload CSV `distance_m,v_kmh`, métricas, 3 gráficos, top-5
    trechos divergentes). 5 testes novos.
- **Suíte: 139 passam** (125 + 6 governor + 5 overlay + 3 pré-existentes de coleta).
- **Validador de regulamento re-rodado**: 3/4 non-compliant (VW/Scania/Volvo: massa,
  wheelbase 4.4–4.7 m, largura); `vw_31320_copa_truck_racing_copy_correto` **COMPLIANT**
  → candidato a baseline "aproximação por regulamento". Corrigir os 3 muda lap ≥0.5 s →
  precisa OK do Vitor (guardrail de calibração).
- **Backlog produto (ordem proposta)**: (1) ~~presets → regulamento~~ ✅ FEITO;
  (2) Pacejka MF simplificado como `TireModel` opcional (diferencial vs OptimumLap);
  (3) deploy hosted + auth (DISTRIBUTION_OPTIONS opção 1; Streamlit + basic auth em VPS);
  (4) ~~conversor .xrk→CSV p/ overlay~~ ✅ overlay já aceita .xrk direto; (5) otimização de linha = V2.

### Sessão 2026-07-05 (parte 2) — presets + UI
- **Frota consolidada**: Scania/Volvo REMOVIDOS (diferenciação sem fonte + non-compliant CBA).
  Único preset = `volkswagen_31320` = baseline de regulamento (m=4950 kg, wb 3.65 m, gov 200 km/h,
  compliant). Cascavel 80.69 s / Interlagos 133.17 s (uncalibrated, honesto). Baselines de
  regressão regeneradas (3 casos VW: cascavel qual+standing, interlagos qual). Testes agora
  ASSERTAM compliance CBA de todo preset shipped.
- **Overlay .xrk**: `telemetry_converter.list_laps()` + página aceita upload .xrk (lap picker,
  fastest pré-selec) OU CSV multi-volta (split por reset de distância). 10 testes no parser.
- **UI/UX** (agente architect): `.streamlit/config.toml` dark motorsport (bg #11141a, accent
  laranja #f28a1f), headers uniformizados, sidebar com branding SARU, `docs/UI_UX_AUDIT.md`
  com backlog P1/P2/P3. Verificado rodando (`.venv/bin/streamlit run ...`, JSON fallback,
  sim Interlagos OK, governador 200 km/h ativo). **Suíte: 143 verdes.**
- **P1 backlog UI (não aplicado)**: (P1-01) results.py 624 linhas → `st.tabs`
  [Overview/Dynamics/Driver/Sectors] ~2d; (P1-02) `theme.py` c/ paleta Plotly unificada ~4h
  (hoje traces ainda usam cores default Plotly); (P1-03) fluxo guiado Parameters→Track→Run ~1d.
- **Docker**: NÃO subir compose deste repo — conflita 5432 c/ saru-os-postgres (rodando).
  App roda 100% JSON fallback local. Deploy real = VPS isolada (DISTRIBUTION_OPTIONS opção 1).
- **Branch**: `feature/claude-product-upgrade` (não mergeada em develop — aguarda OK).

### Sessão 2026-07-06 (parte 2) — Épico full-physics + Fase 1 racing line
- **VIRADA registrada** (§1, §5): full physics IN SCOPE aqui; QSS simples → Hase.
  Plano faseado: `docs/FULL_PHYSICS_PLAN.md` (F1 racing line ✅ · F2 3DOF · F3 freio 3 níveis ·
  F4 viz solver · F5 pistas calendário).
- **Fase 1 — Racing line ✅**: `src/tracks/racing_line.py` (min-curvature via bounded LS
  `lsq_linear` sobre offset lateral α∈[-1,1] dentro das boundaries HDF5; metodologia aberta TUM).
  Solver segue o traçado via flag `use_racing_line` (default OFF → QSS baseline/Hase intacto,
  157 testes verdes). Toggle na página Track + traçado desenhado no mapa (laranja sólido sobre
  centerline tracejada) — resolve o "driver só segue centerline" (ponto 6).
- **GUARDRAIL — Δ medido (aguarda decisão Vitor)**:
  - Cascavel 80.69 → **76.36s** (real pole 79.505 → agora **overshoot -3.1s**: µ estava
    co-calibrado com a centerline pessimista).
  - Interlagos 133.17 → **122.75s** (real Andre Marques 124.7 → de +7.5s de erro para ~-2s).
    **Confirma: a centerline era a fonte dominante do erro de canais/lap.**
  - **DECISÃO PENDENTE**: (a) tornar racing line o default + **recalibrar µ p/ reancorar
    Cascavel em 79.5** (µ desce); (b) validar via overlay vs .xrk (traço de velocidade, não só lap).
    Isso muda lap do default → precisa OK explícito (guardrail). Ferramenta de validação pronta.
- **Próximas fases** (queued, tasks #8-11): 3DOF (ARB vivo), freio 3 níveis (simple/hardware/
  térmico validado) + curva de bias, viz do solver, pistas do calendário (bloqueio de geometria).

### Sessão 2026-07-06 — otimizador honesto, overlay+compare, ARB
- **ARB no solver — FINDING (não é bug)**: ARB é **intrinsecamente inerte** no lap time num
  solver ponto-massa QSS. No limite de curva o eixo carregado satura perto do mesmo piso de grip
  independente do balanço de rigidez (testado: limite bicicleta + sensibilidade de carga por-roda
  convexa — ambos deixaram ARB chapado). ARB afeta balanço **transiente** (turn-in/mid-corner) →
  exige 14DOF (IP SARU, fora deste repo). Hacks revertidos, solver intacto (150 testes verdes).
- **Otimizador honesto**: `optimization.py` agora busca só **asa × pressão** (os knobs que mexem
  no lap). ARB/brake bias removidos da busca (inertes). Grid vira heatmap asa×pressão que **varia**
  de verdade (Cascavel ótimo: wing 9 / 1.4 bar → **79.9 s**, vs pole real 79.505 s). Nota de roadmap
  ARB→14DOF na página.
- **Overlay = ferramenta única** (Compare aposentado, arquivado):
  - Picker das 4 voltas reais bundled (`_quarantine/Perez-data/*.xrk`) + upload manual.
  - Análise de delta (Δv, Δt cumulativo, RMSE, piores trechos) + **multi-canal** sim-vs-real
    (Long-G, Lat-G, throttle, brake) dos canais do .xrk. Verificado rodando: Andre Marques
    Interlagos, Δt sim +7.5 s (centerline ruidoso, esperado).
- **Batch aposentado** (arquivado): redundante com o sweep da Optimization.
- **Router final (6 páginas)**: Parameters · Track · Simulation · Results · Telemetry Overlay · Optimization.
- **PENDENTE P0b (calibração honesta toward real)**: usar o overlay vs Cascavel real (âncora
  1:19.505) p/ identificar onde o sim perde/ganha e ajustar µ/aero/torque DENTRO do regulamento.
  Muda lap ≥0.5 s → reportar Δ e ter OK do Vitor ANTES de commitar (guardrail). Ferramenta agora
  pronta (picker + multi-canal). Cascavel é a âncora; Interlagos bloqueado (traçado ruidoso).

### Sessão 2026-07-05 (parte 3) — auditoria params + P1-02 + freio
- **P1-02 (paleta Plotly)** ✅ `src/visualization/theme.py`: template dark `lts_dark`
  (default global) + tokens semânticos (ACCENT #f28a1f/REFERENCE/POSITIVE/NEGATIVE/LATERAL...).
  ~25 cores hardcoded trocadas em results/overlay/track/optimization/torque_curve. Plots agora
  fundo transparente dark, sem cara de "Plotly default". 152 testes verdes.
- **AUDITORIA de linkage frontend↔solver (resposta ao Vitor)**:
  - **Nenhum param exposto no frontend é órfão** — todos chegam ao solver. Renames OK:
    `wheel_radius`→`r_wheel`, `max_torque`→`T_max` (fallback analítico; torque_curve manda
    quando presente, `_engine_torque` L578).
  - **Params MORTOS** (serializam em to_solver_dict mas solver ignora — sobras do
    ENDURANCE_THERMAL removido): `disc_mass_kg`, `disc_specific_heat`, `disc_convection`,
    `disc_area_m2`, `disc_initial_temp_c`, `disc_thermal_efficiency`, `fade_onset_temp_c`,
    `fade_full_temp_c`, `fade_min_factor`, `downshift_rpm`, `upshift_rpm`. NÃO expostos no
    frontend. **Pendência**: podar de `BrakeParams`/`to_solver_dict`/`from_solver_dict`
    (cuidado: `test_vehicle_mapping` roundtrip). Baixo risco, cosmético.
  - `k_roll` total: redundante (front+rear é que o solver usa; total é dropado).
- **Freio a partir de hardware (ponto 2)**: `src/vehicle/brake_hardware.py` — cadeia de
  Limpert (`clamp = P×A×n; torque = 2·μ_pad·clamp·R_disc; F = torque/R_wheel`), pura, 7 testes.
  **NÃO wirado no solver** — precisa números reais (prompt em `docs/research/PROMPT_brake_hardware.md`,
  Vitor roda) + aprovação (muda lap ≥0.5 s, guardrail). Hoje solver segue usando `max_brake_force`
  slider + cap `max_decel`, ambos batendo no limite físico de grip via `_bias_limited_decel`.
- **Docker (esclarecimento)**: NÃO estão misturados. São 2 projetos docker independentes —
  `copa_truck_db`/`copa_truck_app` (este repo) vs `saru-os-*` (platform/saru-os). Única
  sobreposição: ambos default postgres na porta host 5432. saru-os roda agora e ocupa 5432;
  subir o compose deste repo sem `.env DB_PORT=5433` colide. Não é confusão de projeto,
  é colisão de porta default. App roda 100% JSON fallback local (não precisa do compose p/ demo).

---

## 1. Identidade

> ⚠️ **VIRADA ESTRATÉGICA 2026-07-06 (decisão explícita do Vitor)**: o desacoplamento
> MVP de 30/jun foi **REVERTIDO**. lts-copatruck passa a ser o **sim AVANÇADO** (física
> completa: racing line, 3DOF, freio modelado hardware+térmico validado). O **QSS ponto-massa
> simples atual** é que vira o **produto do Hase** (mais simples). A regra "não inserir 3DOF/
> térmico aqui" está **CANCELADA** — ver §5. Motivo: modelo simples não dá realismo (ARB inerte,
> centerline errada, freio raso); Vitor quer o sim que se aproxima do real p/ validar vs .xrk.

- **Produto**: Lap time simulator Copa Truck — **Sim avançado (full physics)** ⟵ era MVP simples
- **GitHub**: `vitormtt/LTS_CopaTruck` — **NUNCA deletar** (repo ativo do produto)
- **Local**: `~/Projects/SARU/partnerships/lts-copatruck/`
- **Branch ativa**: `feature/claude-product-upgrade`
- **Parceria**: Pérez (pós-graduação). O QSS simples derivado deste repo vai p/ o Hase.

---

## 2. Estado Atual (2026-07-03)

### Testes
- **125 testes passam** (`.venv/bin/python -m pytest -q`, venv `uv` local funcional).
- ⚠️ Passar não valida física: em 2026-07-02 os baselines de regressão foram regenerados e
  o assert de Cascavel afrouxado (76–82 s → 70–82 s) junto com a edição dos presets — ver §6.

### Solver & física
- **Solver**: Two-pass QSS 2DOF (forward + backward) — Ponto massa validado.
- **Combustível**: BSFC dinâmico (power × dt); massa queimada alimenta dinâmica
- **Pneu**: Friction circle + load transfer quasi-estático
- **Freios**: Simples. (Modelos térmicos e IP avançada como `ENDURANCE_THERMAL` foram removidos).
- **Transmissão**: Automática (hysteresis downshift, shift-time traction cut)
- **Aero**: Cd/Cl constante por veículo

### Veículos (`data/vehicle_models.json`)
- `volkswagen_31320` (default), `scania_r480`, `volvo_fh16`, `vw_31320_copa_truck_racing_copy_correto`
- ⚠️ Working tree ≠ HEAD desde 2026-07-02 21:04 (migração ZF 6M + contaminação de params de carro — §6)

### Pistas (`tracks/*.hdf5`)
- `cascavel.hdf5`, `interlagos.hdf5` (brasilia.hdf5 não existe mais no repo)

---

## 3. Desacoplamento & Simplificação (2026-06-30)

- **Total Desacoplamento**: O projeto **não** depende mais do `saru-core`. As importações de engine (`test_dynamic_fuel.py`, `test_torque_curve.py`) voltaram a usar os módulos locais `src.vehicle.engine`.
- **IP Removida**: A classe `ENDURANCE_THERMAL` e toda a física térmica de discos de freio (fade, temps) foram extirpadas do código (`lap_time_solver.py`, `simulation_modes.py`, `results.py`, `simulation.py`). A complexidade foi mantida em ponto massa / QSS 2DOF, suficiente para o Pérez.

---

## 4. Arquitetura

```
src/
  simulation/
    lap_time_solver.py    ← core (two-pass QSS, telemetria rica baseada em cinemática/dinâmica)
    simulation_modes.py   ← SimulationConfig (Qualifying, Standing Start)
    kpis.py
  vehicle/
    parameters.py         ← VehicleParams + sub-dataclasses
    fleet/                ← pacote (cache TTL 5s, PostgreSQL/JSON fallback)
    engine.py             ← ICEEngine local restaurado
    setup.py
  tracks/
    hdf5.py               ← CircuitHDF5Reader/Writer (schema próprio, manter)
    circuit.py
    generator.py          ← TUM FTM + OSM downloader
  database/
    db_manager.py         ← PostgreSQL + JSON fallback
    vehicle_mapping.py    ← decompose/recompose VehicleParams ↔ relacional
    migrate.py
  visualization/
    interface.py          ← Streamlit (Sem gráficos termais)
```

---

## 5. Regras Críticas

1. **Nunca alterar two-pass solver** sem cross-validation contra lap times conhecidos.
2. **Testes antes de commit** — Garantir que 100% da suíte continue passando localmente isolada.
3. ~~**Não inserir IP da SARU** — Modelos 3DOF, 14DOF e térmicos~~ **CANCELADA 2026-07-06**
   (virada estratégica §1). 3DOF, racing line e freio térmico agora são **IN SCOPE** aqui.
   14DOF transiente segue no saru-core (não é foco deste repo). Físicas avançadas entram
   por trás de flags/seletor de modelo (o QSS simples continua selecionável = base do Hase).
4. **Params físicos**: todos via VehicleParams JSON ou HDF5, nunca hardcode.
5. **Guardrail de calibração vale mais que nunca**: toda mudança de física que mexe lap ≥0.5s
   → reportar Δ + overlay vs .xrk real ANTES de commitar. Épico não dispensa validação.

---

## 6. Auditoria e Calibração (2026-07-03) — SoT: `docs/CALIBRATION_AUDIT_2026-07-03.md`

**1. Infraestrutura do MVP (verificado em runtime)**
- **Docker**: infra completa existe (`Dockerfile` multi-stage + `docker-compose.yml` com app
  Streamlit + Postgres 16 + healthchecks + init schema), **mas nenhum container do projeto
  roda hoje** (`docker ps`: só stack saru-os).
- **Banco**: PostgreSQL implementado (`db_manager` + schema + mapping), porém **não usado em
  runtime**: sem `.env`, conexão a `localhost:5432` (que é o Postgres do saru-os) falha auth e
  o app opera 100% em **fallback JSON** (`data/vehicle_models.json` = fonte real dos presets).
- ⚠️ Porta: subir o compose deste repo conflita com saru-os-postgres (5432). Usar `DB_PORT=5433` no `.env`.
- Distribuição p/ Pérez: avaliação em `docs/DISTRIBUTION_OPTIONS.md` (recomendação: hosted).

**2. Validação de lap time (medida 2026-07-03, working tree)**
| Pista | Pole PRO 2025 | Sim HEAD (12M) | Sim working tree (6M+params carro) |
|---|---|---|---|
| Cascavel | 1:19.505 | VW **1:19.591 (Δ+0.086 s)** | VW **1:14.368 (Δ−5.1 s)** ❌ |
| Interlagos | 2:03.905 | VW 2:11.543 (Δ+7.6 s) | VW 2:06.268 (Δ+2.4 s) — cancelamento de erros, não calibração |

- Refs .xrk (Qualy, levantadas 2026-07-02): 2:04.683 (Andre Marques), 2:06.003 (Jô Augusto);
  web: 2:04.876 (Totti) / 2:05.252 (Pole Elite 2025).
- Interlagos tem erro dominado pelo centerline ruidoso (~+4 s, LTS_RESEARCH §5) — validar lá
  só após recaptura do traçado a partir dos GPS dos .xrk.

**3. Estado dos presets (working tree, editado 2026-07-02 21:04, NÃO commitado)**
- ✅ Migração estrutural correta: ZF 6M (6.75…0.78), final_drive 3.42, r_wheel 0.52.
- ❌ Contaminação com bloco de carro GT colado nos 4 presets: h_cg 0.68 m, A_front 4.8 m²,
  Cl −0.5, Iz 7000, wheelbase 3.0 m — quebrou a âncora de Cascavel (5–6 s rápido demais).
- ❌ Testes afrouxados na mesma edição (assert Cascavel 76–82→70–82 s; baselines regeneradas).
- ❌ Validador de regulamento: 4/4 presets non-compliant (massa, wheelbase, largura).
- Diferenciação Scania/Volvo é ficção sem fonte (Copa Truck equaliza via pop-off).
- **Decisão pendente (Vitor)**: opção A (recomendada) = `git restore` presets+testes p/ HEAD e
  refazer migração ZF num preset experimental `*_zf6_reference` com recalibração; opção B =
  corrigir em cima do working tree. Detalhe no doc de auditoria §4.

**4. Pesquisa externa (Vitor executa — agente só prepara)**
- 7 prompts prontos no doc de auditoria §5 (P1 limitador de velocidade, P2 h_cg/Iz, P3 aero,
  P4 pneu/µ, P5 transmissão real, P6 curvas de torque, P7 frenagem). Regra: ≥2 fontes,
  resultados em `docs/research/`, só então promover valores aos presets.
- Governador 200 km/h hardcoded (`lap_time_solver.py:311`) domina a Vmax nas 2 pistas — P1 é
  o prompt de maior impacto.

---

## 7. Pendências

- [ ] **Decidir opção A/B** p/ working tree dos presets (auditoria §4) — bloqueia commit
- [ ] **Rodar prompts P1–P7** no Perplexity/Gemini → `docs/research/` (calibração honesta)
- [ ] **Recapturar centerline Interlagos** dos GPS dos .xrk (pré-requisito p/ validar lá)
- [ ] **Calibrar µ/torque/aero** via `scripts/calibrate_vehicle.py` contra .xrk (gate: |Δ|≤0.5 s Cascavel)
- [ ] **Pérez params**: params físicos reais (bloqueio externo)
- [x] **Venv própria**: criar `uv` venv local isolada (pyproject.toml) para facilitar o repasse ao Pérez.

---

## 8. Histórico relevante

- **2026-06-27**: Fase 1+2+3parcial do merge concluídas.
- **2026-06-30**: Refatoração profunda para entregar o repositório como MVP desacoplado (sem saru-core) e limpo de IP (sem modelos termais/3DOF) para o Pérez. Testes validados.
- **2026-07-02**: Sessão paralela criou `docs/DISTRIBUTION_OPTIONS.md` e às 21:04 editou presets (migração ZF 6M correta + contaminação com params de carro) e afrouxou testes — mudanças não commitadas.
- **2026-07-03**: Auditoria completa de calibração (`docs/CALIBRATION_AUDIT_2026-07-03.md`): lap times medidos HEAD vs working tree, validador de regulamento rodado, infra docker/banco verificada em runtime, 7 prompts de pesquisa preparados.
