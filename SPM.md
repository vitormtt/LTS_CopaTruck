# SARU Project Memory — LapTimeSimulator_CopaTruck

> Última atualização: 2026-07-05
> LER ao iniciar. ATUALIZAR ao final de cada tarefa.

---

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

- **Produto**: Lap time simulator Copa Truck — **MVP Simples / Acadêmico (Pérez)**
- **GitHub**: `vitormtt/LTS_CopaTruck` — **NUNCA deletar** (repo ativo do produto)
- **Local**: `~/Projects/SARU/partnerships/lts-copatruck/`
- **Branch ativa**: `develop`
- **Parceria**: Pérez (pós-graduação) — O repositório foi simplificado e desacoplado do `saru-core` para ser entregue como MVP sem IP proprietária avançada.

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
3. **Não inserir IP da SARU** — Modelos 3DOF, 14DOF e térmicos avançados **não** devem ser colocados neste repositório.
4. **Params físicos**: todos via VehicleParams JSON ou HDF5, nunca hardcode.

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
