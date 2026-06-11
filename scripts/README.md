# scripts/ — Calibração e Sensibilidade

Ferramentas CLI do pipeline de aprendizado do LTS (ver
`docs/LTS_RESEARCH.md` para a fundamentação).

## sensitivity_analysis.py — tornado OAT

Quais parâmetros mais movem o lap time (one-at-a-time ±pct%):

```bash
python3 scripts/sensitivity_analysis.py --vehicle volkswagen_31320 \
    --track cascavel --pct 10
# subconjunto: --params mu mass torque_scale | sem salvar: --no-save
```

Saída: tabela tornado no stdout + relatório Markdown/CSV em `src/results/`.

## calibrate_vehicle.py — calibração contra telemetria real

Ajusta [mu, Cd, Cl, torque_scale, max_decel, brake_balance] para casar o
traço de velocidade simulado com uma volta de referência (RMSE de v por
distância + |Δlap|), via differential evolution + least_squares.

```bash
# 1) Converter a telemetria real (uma vez; requer libxrk):
pip install libxrk
python3 scripts/calibrate_vehicle.py --vehicle volkswagen_31320 \
    --track interlagos \
    --xrk "Perez-data/Jô Augusto_Copa Truck VW 81_Interlagos_Qualifying 1_a_0476.xrz_20250517_130853.xrk"

# 2) Ou direto de um CSV com colunas distance_m,v_kmh:
python3 scripts/calibrate_vehicle.py --vehicle volkswagen_31320 \
    --track cascavel --reference ref.csv

# Rápido (sem o estágio global): --no-de --params mu torque_scale
```

Saída: preset calibrado em `data/<vehicle>_calibrated.json` (formato de
`vehicle_models.json` — copie os campos para o preset oficial após
validação cruzada) + relatório Markdown em `src/results/`.

**Validação cruzada:** calibre numa pista (ex.: Cascavel) e confira o RMSE
na outra (Interlagos) antes de adotar os valores.
