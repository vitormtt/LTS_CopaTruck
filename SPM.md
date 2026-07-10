# SARU Project Memory — LapTimeSimulator_CopaTruck

> Última atualização: 2026-07-10
> LER ao iniciar. ATUALIZAR ao final de cada tarefa.
> Sessões antigas (≤2026-07-08): `SPM_ARCHIVE.md` (registro, não estado).
> Backlog priorizado: `docs/README.md`.

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

> Backlog priorizado vive em **`docs/README.md`** (índice mestre, 2026-07-10).
> Resumo: (1) pipeline track/µ · (2) pesquisa k_roll (prompt pronto) ·
> (3) P2 h_cg/Iz, P5 ratios, P6 curva torque · (4) qualy multi-fase (outlap
> térmico) · (5) brake bias por curva no solver · (6+) ver índice.
- [ ] **Pérez params**: params físicos reais (bloqueio externo)
- [x] Opção A/B presets → resolvido (preset único fundido 2026-07-10)
- [x] Recaptura Interlagos → absorvida pelo pipeline track/µ (doc Validação)

---

## 8. Histórico relevante

- **2026-06-27**: Fase 1+2+3parcial do merge concluídas.
- **2026-06-30**: Refatoração profunda para entregar o repositório como MVP desacoplado (sem saru-core) e limpo de IP (sem modelos termais/3DOF) para o Pérez. Testes validados.
- **2026-07-02**: Sessão paralela criou `docs/DISTRIBUTION_OPTIONS.md` e às 21:04 editou presets (migração ZF 6M correta + contaminação com params de carro) e afrouxou testes — mudanças não commitadas.
- **2026-07-03**: Auditoria completa de calibração (`docs/CALIBRATION_AUDIT_2026-07-03.md`): lap times medidos HEAD vs working tree, validador de regulamento rodado, infra docker/banco verificada em runtime, 7 prompts de pesquisa preparados.
