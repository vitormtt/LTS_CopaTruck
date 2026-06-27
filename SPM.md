# SARU Project Memory — LapTimeSimulator_CopaTruck

> Última atualização: 2026-06-27
> LER ao iniciar. ATUALIZAR ao final de cada tarefa.

---

## 1. Identidade

- **Produto**: Lap time simulator Copa Truck (caminhões diesel, circuitos brasileiros)
- **GitHub**: `vitormtt/LTS_CopaTruck` — **NUNCA deletar** (repo ativo do produto)
- **Local**: `~/Projects/SARU/partnerships/lts-copatruck/`
- **Branch ativa**: `develop` (sincronizada com origin, último push `a5704cd` em 2026-06-27)
- **Parceria**: Pérez (pós-graduação) — aguardando params físicos reais

---

## 2. Estado Atual (2026-06-27)

### Testes
- **107 testes passam** (5 skipped) — 2 ignorados por dep streamlit ausente no venv de testes
- Sem venv próprio funcional (`.venv` existente é Windows/Python 3.14, inutilizável no Linux)
- **Como rodar**:
  ```bash
  /home/vitor/Projects/SARU/platform/saru-core/.venv/bin/python \
    -m pytest -q \
    --ignore=tests/test_model_creation.py \
    --ignore=tests/test_ui_vehicle_params.py
  ```

### Solver & física
- **Solver**: Two-pass QSS 2DOF (forward + backward) — VALIDADO
- **Combustível**: BSFC dinâmico (power × dt); massa queimada alimenta dinâmica
- **Pneu**: Friction circle + load transfer quasi-estático
- **Freios**: Fade térmico (`ENDURANCE_THERMAL` mode) — modelo de disco lumped
- **Transmissão**: Automática (hysteresis downshift, shift-time traction cut)
- **Aero**: Cd/Cl constante por veículo

### Veículos (`data/vehicle_models.json`)
- `volkswagen_31320` (default), `scania_r480`, `volvo_fh16` + presets Porsche/GT3 (calibração)

### Pistas (`tracks/*.hdf5`)
- `cascavel.hdf5`, `interlagos.hdf5`, `brasilia.hdf5` + custom em `tracks/custom/`

---

## 3. Merge Repos — Estado (2026-06-27)

Contexto completo: `/home/vitor/Projects/SARU/MERGE-REPOS-DELETE.md`

### Feito (Fases 0–3 parcial)
| Item | Commit |
|---|---|
| `platform/telemetry-service/lap-analyzer/` deletado | — |
| git init + vinicius structure + push | `bceb63d` |
| 3 testes integração migrados para saru-core | `e5b2c67` (saru-core) |
| ICEEngine: imports migrados para `saru_core.vehicle.engine` | `a5704cd` |

### Módulos NÃO substituídos (decisão permanente)
| Módulo | Manter local por quê |
|---|---|
| `src/tracks/hdf5.py` | HDF5 existentes escritos por este writer; reader saru-core tem schema diferente |
| `src/tracks/generator.py` | Implementações completamente diferentes |
| `src/simulation/simulation_modes.py` | ENDURANCE_THERMAL é `SimulationMode` aqui; `qualifying()` factory só existe aqui; saru-core usa flags |

### Próximo (Fase 3b — PR dedicado saru-core)
- **ENDURANCE_THERMAL extraction** → plugin/option em `saru_core.simulation.qss_solver`
- Não alterar two-pass solver sem cross-validation prévia

---

## 4. Imports — o que vem de onde

```python
# De saru_core (já migrado):
from saru_core.vehicle.engine import ICEEngine

# Local src/ (intencional — ver §3):
from src.simulation.simulation_modes import SimulationConfig, SimulationMode
from src.simulation.lap_time_solver import run_simulation, _torque_curve_interp, _fuel_step
from src.tracks.hdf5 import CircuitHDF5Reader, CircuitHDF5Writer
from src.vehicle.parameters import EngineParams, VehicleParams
from src.vehicle.fleet import get_vehicle_by_id
from src.vehicle.setup import get_default_setup
```

---

## 5. Arquitetura

```
src/
  simulation/
    lap_time_solver.py    ← core (two-pass QSS + ENDURANCE_THERMAL)
    simulation_modes.py   ← SimulationConfig; SimulationMode inclui ENDURANCE_THERMAL
    kpis.py
  vehicle/
    parameters.py         ← VehicleParams + sub-dataclasses
    fleet.py              ← cache TTL 5s, PostgreSQL/JSON fallback
    engine.py             ← DUPLICATA — testes usam saru_core.vehicle.engine agora
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
    interface.py          ← Streamlit
data/
  vehicle_models.json     ← presets canônicos
tracks/                   ← circuitos .hdf5
tests/                    ← 107+ testes pytest
```

---

## 6. Regras Críticas

1. **Nunca alterar two-pass solver** sem cross-validation contra lap times conhecidos
2. **107+ testes antes de qualquer commit** — usar saru-core venv (ver §2)
3. **Não substituir `src/simulation/simulation_modes.py`** sem migrar ENDURANCE_THERMAL ao saru-core primeiro
4. **Não substituir `src/tracks/hdf5.py`** — schema das pistas existentes é do writer local
5. **Params físicos**: todos via VehicleParams JSON ou HDF5, nunca hardcode

---

## 7. Pendências

- [ ] **Fase 3b**: ENDURANCE_THERMAL extraction → PR em saru-core como plugin
- [ ] **Venv própria**: criar `uv` venv com saru-core como dep local (pyproject.toml)
- [ ] **Pérez params**: params físicos reais (bloqueio externo)
- [ ] **3DOF roll dynamics** (roadmap)
- [ ] **Pacejka tire model** (roadmap)
- [ ] **GitHub repos deletar**: aguardar OK do Vitor — ver MERGE-REPOS-DELETE.md §7

---

## 8. Histórico relevante

- **2026-06-04**: Brake Trace Analysis definida como prioridade em telemetria (Segers como referência)
- **2026-06-27**: Fase 1+2+3parcial do merge concluídas; ICEEngine migrado; venv saru-core corrigida
