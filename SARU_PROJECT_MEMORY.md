# SARU Project Memory — LapTimeSimulator_CopaTruck

> Memória contínua entre sessões.
> LER ao iniciar. ATUALIZAR ao final de cada tarefa.
> Última atualização: 2026-05-16

---

## 1. Identidade do Projeto
- **Nome**: LapTimeSimulator_CopaTruck
- **Posição no ecossistema**: CopaTruck
- **Tier**: Intermediário
- **Branch ativa**: main

---

## 2. Estado Atual

### Módulos implementados
- [x] `src/simulation/lap_time_solver.py` — solver two-pass (2DOF bicycle model) — 18/18 testes passando
- [x] `src/vehicle/` — VehicleParams + sub-dataclasses (VehicleMassGeometry, TireParams, AeroParams, EngineParams, TransmissionParams, BrakeParams)
- [x] `src/tracks/` — HDF5 reader/writer, TUM FTM integration
- [x] `src/visualization/interface.py` — Streamlit interface
- [x] `data/vehicle_models.json` — presets: VW 31320, Scania R480, Volvo FH16
- [x] `tracks/*.hdf5` — circuitos em HDF5

### Em desenvolvimento
- [~] `LapTimeSimulator_Generic/` — Generic LTS (nested, scaffold com src/)
- [ ] 3DOF roll dynamics (roadmap)
- [ ] Genetic algorithm setup optimization (roadmap)
- [ ] Pacejka tire model migration (roadmap)

### PAUSED / Bloqueados
- [ ] Frontend customization — aguardando params do Pérez
- [ ] Vehicle params do Pérez (parceiro técnico pós-graduação)

---

## 3. Decisões de Arquitetura

### ADRs
- **ADR-001 — Sistema de Coordenadas**: ISO 8855 — `docs/adr/ADR-001-coordinate-system.md`
- **ADR-002 — Data Versioning**: PENDENTE
- **ADR-003 — SARU API Runtime**: PENDENTE

### Sistema de Coordenadas
- Convenção: ISO 8855 (x frente, y esquerda, z cima)
- Atitude: **quaternion interno** (a implementar na Fase A2), Euler em I/O

### Stack de Dev
- Package manager: `pip` + `requirements.txt` → **migrar para `uv`** na Fase A2
- Validação metadata/APIs: dataclasses atuais → **Pydantic v2** na Fase A2
- Logging & Obs: não implementado → **structlog** na Fase A2
- Container: não implementado → **Docker** na Fase A2

### Regras Golden (do CLAUDE.md)
- Nunca hardcode vehicle/track params — sempre via VehicleParams JSON ou HDF5
- Nunca alterar two-pass solver sem cross-validation contra lap times conhecidos
- pytest 100% antes de qualquer commit
- ABCs totalmente implementadas

---

## 4. Modelos Físicos Definidos

- **Dinâmica atual**: Bicycle model 2DOF (lateral + longitudinal)
- **Target (Plano v3)**: QSS + GGV (Fase A2)
- **Solver**: Two-pass (forward + backward) — VALIDADO
- **Drop test**: não aplicável (modelo QSS)
- **Aero**: constante (Cd, Cl por veículo)
- **Pneu**: Linear/Friction Circle (Cf, Cr, mu) — target: Pacejka MF 5.2
- **Drivetrain**: Engine curve + gearbox (12-16 marchas, diesel) + diff implícito

---

## 5. Parâmetros-Chave (Extraídos de `data/vehicle_models.json`)

| Parâmetro | VW 31320 (default) | Scania R480 | Volvo FH16 | Fonte |
|-----------|-------------------|-------------|------------|-------|
| massa (kg) | 5800 | 6200 | 6000 | vehicle_models.json |
| lf (m) | 2.15 | 2.30 | 2.20 | vehicle_models.json |
| lr (m) | 2.25 | 2.40 | 2.30 | vehicle_models.json |
| Cf = Cr (N/rad) | 135000 | 140000 | 145000 | vehicle_models.json |
| mu | 1.15 | 1.12 | 1.18 | vehicle_models.json |
| r_wheel (m) | 0.65 | 0.67 | 0.66 | vehicle_models.json |
| P_max (W) | 550000 | 600000 | 625000 | vehicle_models.json |
| T_max (Nm) | 2800 | 3200 | 3350 | vehicle_models.json |
| rpm_max | 2600 | 2500 | 2700 | vehicle_models.json |
| n_gears | 12 | 12 | 12 | vehicle_models.json |
| final_drive | 5.33 | 5.42 | 5.25 | vehicle_models.json |
| Cx (Cd) | 0.88 | 0.90 | 0.85 | vehicle_models.json |
| A_front (m²) | 8.9 | 9.2 | 8.8 | vehicle_models.json |
| Cl | 0.05 | 0.08 | 0.03 | vehicle_models.json |

---

## 6. Esquema Universal de Telemetria ("Padrão SARU")

- **Metadados (Pydantic v2)** — a implementar na Fase A2
- **Séries temporais (Pandera + Polars)** em ISO 8855 — a implementar na Fase A2
- Atualmente: CSV export via `src/results/`

---

## 7. Pendências / Riscos Abertos

- [ ] **Fase A2**: migrar para uv + Pydantic v2 + QSS + GGV + Drivetrain completo + Async API
- [ ] Adicionar `LapTimeSimulator_Generic/` como submodule ou mover para repo separado (ambiguidade estrutural)
- [ ] Params do Pérez (parceiro técnico) — bloqueio de frontend

---

## 8. Referências, Dados e Licenças

- `data/vehicle_models.json` — parâmetros VW 31320, Scania R480, Volvo FH16
- `tracks/*.hdf5` — circuitos Copa Truck
- GitHub: vitormtt/LapTimeSimulator_CopaTruck

---

## 9. Operações

- `pip install -r requirements.txt` (→ `uv sync --frozen` após Fase A2)
- `pytest tests/` — deve 100% antes de qualquer commit
- `streamlit run src/visualization/interface.py`
