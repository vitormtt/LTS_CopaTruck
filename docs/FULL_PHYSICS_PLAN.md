# Full-Physics Epic — Plano (2026-07-06)

> **STATUS 2026-07-10**: F1 ✅ FEITA e promovida (racing line always-on +
> corredor por largura de veículo). F3 nível HARDWARE ✅ (Limpert wired,
> valores researched). Restam: F2 3DOF · F3 THERMAL · F4 viz solver · F5
> pistas calendário. **Pré-requisito novo nº 1: pipeline track/µ**
> (docs/Validação de Lap Sim.md) — recalibra µ antes de qualquer fase nova.

> Virada estratégica: lts-copatruck vira o sim avançado (SPM §1). Este doc é o
> roadmap faseado. Cada fase: TDD + cross-validation vs .xrk real (guardrail) +
> reporta Δ lap antes de commit. O QSS ponto-massa simples continua **selecionável**
> (model selector) — é a base que vai pro Hase.

## Princípio de arquitetura
Modelos entram por **seletor/flag**, não substituindo. `SolverModel` enum:
`QSS_POINT_MASS` (atual, = Hase) → `QSS_3DOF` (novo) → futuros. Idem freio:
`BrakeModel` = `SIMPLE` → `HARDWARE` (Limpert) → `THERMAL` (fade, validado).
Racing line = flag `use_racing_line` (default on no avançado).

## Fases (ordem por dependência + valor)

### Fase 1 — Racing line (FUNDAÇÃO) ✅ FEITA (2026-07-06 → 10)
> Entregue: min-curvature (`racing_line.py`), solver dirige a linha SEMPRE
> (2026-07-10, diretiva), corredor descontado pela largura do veículo,
> cache por largura, toggle da UI é viz-only.
- **Por quê 1º**: driver hoje segue centerline (errado, ponto 6). É a raiz do erro
  de canais e do Interlagos +7.5s. Metodologia ABERTA (TUM, Veneri&Massaro) — não é IP.
- `src/tracks/racing_line.py`: min-curvature path dentro das boundaries (QP scipy sobre
  offset lateral α∈[-1,1]). Boundaries já existem no HDF5.
- Solver recomputa raio/curvatura a partir da racing line, não da centerline.
- Cross-val: Cascavel deve **cair** toward 79.5 (linha mais rápida que centerline).
- Desbloqueia: viz do traçado do driver (ponto 4), 3DOF (usa o path).

### Fase 2 — Modelo 3DOF (ARB vivo)
- Yaw/lateral/roll: transferência de carga longitudinal+lateral acoplada à rigidez
  (k_roll front/rear) → forças por pneu → balanço → ARB **muda** o lap.
- Atrás de `SolverModel.QSS_3DOF`. QSS_POINT_MASS intacto.
- Cross-val: ARB deve variar lap; balanço bate com telemetria (yaw, Δv por trecho).

### Fase 3 — Modelos de freio (simples → hardware ✅ → térmico)
> HARDWARE entregue 2026-07-10: Limpert wired com pacote researched
> (Knorr SN7 2×68mm, 314/263 bar equiv, PD/116 µ0.48, R 0.1725) — editável
> na UI, grip-limited (Δlap 0). Falta THERMAL (fade validado vs dados).
- `BrakeModel.SIMPLE` (atual) · `HARDWARE` (Limpert, `brake_hardware.py` já existe:
  pistão/pinça/pressão/μ pastilha/raio disco → força) · `THERMAL` (fade por temp de disco).
- **Térmico precisa validação** (Vitor pediu explicitamente) — re-introduz o que era
  ENDURANCE_THERMAL, agora validado vs dados. Curva de bias vs velocidade/pressão (ponto 3).

### Fase 4 — Visualização do solver (ponto 4)
- Iterações do solver (forward/backward passes), tempo computacional, convergência da
  otimização (já tem curva DE), traçado do driver na pista (racing line vs centerline),
  animação da primeira volta. Página nova "Solver Insight".

### Fase 5 — Pistas do calendário Copa Truck (ponto 5)
- **Bloqueio de dados**: só temos geometria de Cascavel + Interlagos (HDF5). Demais pistas
  do calendário (Goiânia, Curvelo/Velo Città, Santa Cruz do Sul, Tarumã, Londrina, Campo
  Grande, Guaporé, Interlagos, Cascavel...) **não estão em bases abertas** (TUM não tem
  truck-tracks BR). Precisam de captura GPS (.xrk) ou OSM. Agente **não fabrica geometria**.
  → Listar calendário + sinalizar quais têm dado (2) vs quais precisam captura (resto).

## Guardrails do épico
- QSS_POINT_MASS **nunca** regride (é o produto Hase). Testes de regressão o protegem.
- Cada fase valida vs Cascavel (âncora 1:19.505). Interlagos só após racing line (traçado
  ruidoso hoje é justamente o problema que a racing line resolve).
- Δ lap ≥0.5s → reporta + OK do Vitor antes do commit.
