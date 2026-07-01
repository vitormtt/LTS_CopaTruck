# SARU Project Memory — LapTimeSimulator_CopaTruck

> Última atualização: 2026-06-30
> LER ao iniciar. ATUALIZAR ao final de cada tarefa.

---

## 1. Identidade

- **Produto**: Lap time simulator Copa Truck — **MVP Simples / Acadêmico (Pérez)**
- **GitHub**: `vitormtt/LTS_CopaTruck` — **NUNCA deletar** (repo ativo do produto)
- **Local**: `~/Projects/SARU/partnerships/lts-copatruck/`
- **Branch ativa**: `develop`
- **Parceria**: Pérez (pós-graduação) — O repositório foi simplificado e desacoplado do `saru-core` para ser entregue como MVP sem IP proprietária avançada.

---

## 2. Estado Atual (2026-06-30)

### Testes
- **101 testes passam** (5 skipped) — Suíte limpa de dependências externas e testes termais removidos.
- Sem venv próprio funcional local (usando pytest global ou do saru-core para execução).

### Solver & física
- **Solver**: Two-pass QSS 2DOF (forward + backward) — Ponto massa validado.
- **Combustível**: BSFC dinâmico (power × dt); massa queimada alimenta dinâmica
- **Pneu**: Friction circle + load transfer quasi-estático
- **Freios**: Simples. (Modelos térmicos e IP avançada como `ENDURANCE_THERMAL` foram removidos).
- **Transmissão**: Automática (hysteresis downshift, shift-time traction cut)
- **Aero**: Cd/Cl constante por veículo

### Veículos (`data/vehicle_models.json`)
- `volkswagen_31320` (default), `scania_r480`, `volvo_fh16` + presets Porsche/GT3 (calibração)

### Pistas (`tracks/*.hdf5`)
- `cascavel.hdf5`, `interlagos.hdf5`, `brasilia.hdf5` + custom em `tracks/custom/`

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
    fleet.py              ← cache TTL 5s, PostgreSQL/JSON fallback
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

## 6. Pendências

- [ ] **Pérez params**: params físicos reais (bloqueio externo)
- [x] **Venv própria**: criar `uv` venv local isolada (pyproject.toml) para facilitar o repasse ao Pérez.

---

## 7. Histórico relevante

- **2026-06-27**: Fase 1+2+3parcial do merge concluídas.
- **2026-06-30**: Refatoração profunda para entregar o repositório como MVP desacoplado (sem saru-core) e limpo de IP (sem modelos termais/3DOF) para o Pérez. Testes validados.
