# LTS — Estado da Arte, Iterações e Roteiro de Aprendizado

> Pesquisa de fundamentação para o LTS Copa Truck (SARU Dynamics).
> Data: 2026-06-11.

## 1. Taxonomia dos métodos de Lap Time Simulation

| Método | Como resolve | Custo/volta | Uso típico |
|--------|--------------|-------------|------------|
| **QSS ponto-de-massa / GGV** (o nosso) | Forward/backward pass sobre a linha; limites do círculo de atrito por ponto | ~10–50 ms | Estudos de setup e sensibilidade; calibração |
| QSS multi-DOF (7DOF GG-diagram) | GGV gerado por modelo de equilíbrio multi-corpo; mesma varredura | ~s | Balance/setup detalhado (Brayshaw & Harrison 2005) |
| QSS free-trajectory | QSS + otimização da trajetória (não só da velocidade) | ~min | Quando a linha importa (Veneri & Massaro 2019) |
| Optimal control transiente | Minimum-time OCP com modelo dinâmico completo (ex.: GP2 14DOF) | ~min–h | Pesquisa, validação fina (Perantoni & Limebeer) |
| Transiente + driver model (14DOF) | Integração temporal em malha fechada | ~min–h | **LTS_SARU** — fora do escopo deste LTS |

**Por que QSS para este LTS:** o objetivo aqui é OTIMIZAR (setup, calibração,
sensibilidade), o que exige milhares de voltas simuladas. O QSS da TUM FTM
(Heilmeier et al. 2019) — referência open-source do método — usa exatamente a
nossa arquitetura de varreduras e é o padrão para "parameter studies within a
few minutes". A limitação conhecida (dinâmica transitória de rolagem/balance
não capturada) é mitigada no nosso caso pelas extensões quase-estáticas
(transferência de carga por eixo, cap de guinada via Iz) e é o nicho do
LTS_SARU 14DOF.

## 2. Iterações — o que roda no nosso solver

- **Por volta:** 3 varreduras deterministicas sobre n pontos do traçado
  (forward de aceleração máxima, backward de frenagem, integração de tempo).
  Não há laço de convergência; ~30 ms/volta com n=3000.
- **ENDURANCE_THERMAL:** + até 3 iterações de ponto-fixo fade↔frenagem
  (monotônicas, convergem porque o fade só reduz capacidade).
- **Otimização de setup:** Grid Search (até 441 voltas) ou Differential
  Evolution (popsize×maxiter voltas, com curva de convergência).
- **Calibração:** 20–200 voltas por execução (least_squares; DE global
  quando o ponto de partida é ruim).

## 3. Reduzindo o erro vs realidade — pipeline de calibração

Princípio (validação padrão da literatura, e.g. Perantoni & Limebeer):
comparar **traço de velocidade por distância** e acelerações com telemetria
real — não apenas o tempo de volta (dois erros podem se cancelar no lap).

Pipeline implementado (`scripts/calibrate_vehicle.py`):
1. **Referência**: volta mais rápida dos .xrk reais (Perez-data/, AiM) via
   `telemetry_converter` (requer `libxrk`), ou qualquer CSV
   `distance_m,v_kmh`.
2. **Alinhamento**: reamostragem sim+ref numa grade comum de distância.
3. **Objetivo**: RMSE(v) + peso·|Δlap| (composto; o peso evita degenerar).
4. **Otimização**: `differential_evolution` (global, bounds físicos) +
   polimento `least_squares`. Parâmetros livres: µ, Cd, Cl, escala de torque,
   max_decel, brake_balance — apenas parâmetros VIVOS e incertos (o
   governador de 200 km/h é regulamento, fixo).
5. **Validação cruzada**: calibrar em um piloto/pista e validar em outro
   (temos Interlagos E Cascavel nos .xrk — usar um para fit, outro p/ teste).

Round-trip sintético (teste automatizado): perturbação µ×0,95/torque×1,05 é
recuperada com erro <3% em ~23 execuções do solver.

## 4. Envelope do piloto ("o que o carro E o piloto conseguem")

O QSS assume piloto perfeito (100% dos limites, inputs binários). Para
aproximar "a melhor volta que o piloto consegue realizar":
1. Extrair o **diagrama GG realizado** dos .xrk (a_lat × a_long usados de
   fato) e comparar com o GG simulado — a razão entre as envoltórias é o
   "fator piloto" por região (frenagem, tração, combinado).
2. Aplicar como escala dos limites do solver (µ_eff por quadrante) →
   simulação da "melhor volta realizável", não da volta teórica.
3. Roadmap: suavização de inputs (jerk limit do volante/pedais) como
   penalidade quase-transiente — base já existe no cap de guinada via Iz.

## 5. Prioridades de evolução (ordem de custo/benefício)

1. ✅ Física v2 (P_max, aero, telemetria, subsistemas vivos) — pré-requisito
   de qualquer calibração honesta.
2. `pip install libxrk` + converter os 4 .xrk → calibrar µ/Cd/torque por
   pista; validação cruzada Interlagos↔Cascavel.
3. Fator piloto via GG realizado (item 4).
4. Free-trajectory (otimizar a linha, não só a velocidade) — ganho grande em
   fidelidade de Interlagos; custo médio.
5. Qualidade do traçado: o interlagos.hdf5 tem 862 pts (~5 m) e curvatura
   ruidosa; recapturar centerline dos próprios GPS dos .xrk é melhor que
   reamostrar spline (a reamostragem amplificou ruído de curvatura: +4 s).

## Referências

- Brayshaw, D.L. & Harrison, M.F. (2005). *A quasi steady state approach to
  race car lap simulation...* Proc. IMechE Part D.
  https://journals.sagepub.com/doi/10.1243/095440705X11211
- Heilmeier, Geisslinger & Betz (2019). *A Quasi-Steady-State Lap Time
  Simulation for Electrified Race Cars.* IEEE ICEERE.
  https://ieeexplore.ieee.org/document/8813646/ — código:
  https://github.com/TUMFTM/laptime-simulation
- Perantoni, G. & Limebeer, D.J.N. *Minimum time optimal control simulation
  of a GP2 race car.*
  https://eprints.soton.ac.uk/417133/1/GP2manuscriptPURE_002_.pdf
- Veneri, M. & Massaro, M. (2019). *A free-trajectory quasi-steady-state
  optimal-control method for minimum lap-time of race vehicles.*
  https://www.researchgate.net/publication/332637470
- Milliken & Milliken (1995). *Race Car Vehicle Dynamics.* SAE.
- Limpert, R. (1999). *Brake Design and Safety.* SAE.
