# LapTimeSimulator_CopaTruck — CLAUDE.md (SARU Course)

## Stack deste repositório

@.claude/rules/python.md
@.claude/rules/streamlit.md

<!-- regras de escopo restrito — não ativar neste repo -->
<!-- @.claude/rules/fastapi.md    → apenas repos com backend FastAPI -->
<!-- @.claude/rules/matlab.md     → apenas fullvehiclesimulation_fsae -->
<!-- @.claude/rules/nestjs.md     → apenas automotiveportfolio_global (SARU Hub) -->

## Stack declarado

| Camada | Tecnologia | Status |
|--------|-----------|--------|
| Kernel/cálculo | Python 3.11 + NumPy/SciPy | ativo |
| Interface | Python 3.11 + Streamlit | ativo |
| Frontend web | Next.js (React/TS) | não planejado para este produto |
| Infra | local (sem Docker por enquanto) | — |

---

## Context
- Lap time simulator para Copa Truck — SARU Course (SARU Dynamics)
- Parceria técnica: Pérez (pós-graduação)
- GitHub: vitormtt/LapTimeSimulator_CopaTruck
- Caminho local Ubuntu: `~/Projects/laptimesimulator_copatruck`

> **Este arquivo (`CLAUDE.md`) é um documento vivo** — atualizar sempre que arquitetura, convenções ou sequências mudarem.

---

## Project Architecture

```
LapTimeSimulator_CopaTruck/
├── src/
│   ├── simulation/          ← lap_time_solver.py — solver principal (two-pass)
│   ├── vehicle/             ← VehicleParams e sub-dataclasses
│   ├── tracks/              ← HDF5 reader/writer, TUM FTM integration
│   ├── visualization/       ← interface Streamlit (interface.py)
│   ├── optimization/        ← otimização de setup (futuro)
│   └── results/             ← telemetria exportada .csv
├── tracks/                  ← arquivos de circuito (.hdf5)
├── data/                    ← presets de veículo (.json)
├── tests/                   ← pytest — 100% antes de qualquer push
├── docs/                    ← documentação técnica
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Simulation Model

**Bicycle Model 2DOF** com extensões:
- Lateral: forças de cornering (Cf, Cr)
- Longitudinal: tração limitada por grip + arrasto aerodinâmico
- Motor: curva de torque diesel realista (pico ~1300 RPM)
- Transmissão: troca automática de marchas (banda 1200–2200 RPM)
- Freios: círculo de atrito (desaceleração máxima respeitando a_lat)

### Forward-Backward Solver (Two-Pass)
1. **Forward pass**: aceleração máxima respeitando tração e limites laterais
2. **Backward pass**: frenagem para não exceder a velocidade de entrada na curva
- **Nunca alterar o método two-pass sem cross-validation contra tempos conhecidos.**

---

## OOP Architecture

### Dataclasses (SSoT de parâmetros)
```python
@dataclass class VehicleMassGeometry  # massa, wheelbase, CG, inércias
@dataclass class TireParams            # Cf, Cr, mu, raio da roda
@dataclass class AeroParams            # Cd, área frontal, Cl
@dataclass class EngineParams          # potência, torque, RPM
@dataclass class TransmissionParams    # marchas, relações, desmultiplicação
@dataclass class BrakeParams           # força máx, balanceamento, desaceleração
@dataclass class VehicleParams         # compõe todos os sub-dataclasses
```
- `__repr__` obrigatório em todos os dataclasses.
- `VehicleParams` é o SSoT — nunca hardcodar constantes fora dele.
- Preset default: `copa_truck_2dof_default()` (Mercedes-Benz Actros 600 kW).

### ABCs (subsistemas intercambiáveis)
```python
class TireModel(ABC):    ← PacejkaModel, LinearTireModel
class Solver(ABC):       ← TwoPassSolver (extensível)
class TrackLoader(ABC):  ← HDF5Loader, TUMFTMLoader
```
- ABCs definem contratos de interface — nenhuma subclasse pode deixar método abstrato não implementado.
- Trocar modelo de pneu ou solver não deve exigir mudanças fora do módulo.

### Regra de composição
- `LapSimulator` **contém** `VehicleParams`, `Track`, `Solver` — nunca herda deles.
- Herança apenas para relacionamentos IS-A genuínos.

---

## SSoT — Parameters

| Fonte | Conteúdo |
|-------|----------|
| `data/<nome>.json` | Preset de veículo (VehicleParams serializado) |
| `tracks/<nome>.hdf5` | Geometria do circuito (centerline, limites, largura) |

- **Nunca hardcodar valores de veículo ou pista** — sempre carregar via JSON ou HDF5.
- Novo veículo: via `VehicleParams` e `.save_to_json()`.
- Novo circuito: via `CircuitData` e `CircuitHDF5Writer`.

---

## Circuit Format (HDF5)

HDF5 comprimido com:
- `centerline_x`, `centerline_y`
- Limites esquerdo/direito
- Largura da pista
- Metadados: nome, comprimento, sistema de coordenadas

Fontes: TUM FTM (`src/tracks/tumftm.py`), geradores customizados (`src/tracks/generator.py`).

---

## Code Standards

Ver `.claude/rules/python.md` e `.claude/rules/streamlit.md` para convenções completas.

### Git — Conventional Commits
```
feat:     nova feature ou capacidade de simulação
fix:      bug fix ou correção de parâmetro
refactor: reestruturação sem mudança de comportamento
sim:      atualização de resultado ou cenário
docs:     README, comentários, CLAUDE.md, relatórios
chore:    limpeza, config, tooling, dependências
test:     adicionar ou atualizar testes de validação
perf:     melhoria de performance (velocidade do solver, memória)
```

---

## Status (2026)
- Solver principal: completo e validado (18/18 testes)
- Pendente: customização frontend + parâmetros de veículo do Pérez
- Roadmap: dinâmica 3DOF, otimização genética de setup, modelo de pneu Pacejka, comparação multi-volta

---

## Golden Rules for Claude

1. **Nunca hardcodar parâmetros de veículo ou pista** — sempre via `VehicleParams` JSON ou HDF5.
2. **Nunca alterar o two-pass solver** sem cross-validation contra tempos conhecidos.
3. **pytest deve passar 100%** antes de qualquer commit proposto.
4. **ABCs devem ser completamente implementadas** — nenhum método abstrato sem implementação.
5. **Manter este arquivo atualizado** — quando propor mudanças estruturais, incluir diff do CLAUDE.md.
