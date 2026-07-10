# Prompt de pesquisa — hardware de freio Copa Truck (para derivar max_brake_force)

> **✅ RESPONDIDO (2026-07-10)** — resposta em `docs/Especificações Freio Copa Truck.md`; valores APLICADOS (preset + brake_hardware wired, commits 1b33bd2/40cf6f5). Prompt mantido como registro.

> Regra de ouro: Vitor executa no Gemini/Perplexity. Agente só prepara.
> Objetivo: substituir o `max_brake_force`/`max_deceleration` mágico por um valor
> DERIVADO do hardware real, via `src/vehicle/brakes.py` (cadeia de Limpert já implementada).
> Gate: valores só entram no preset após ≥2 fontes E aprovação do Vitor (mudam lap ≥0.5 s).

## O que o solver precisa (por eixo)

A função `brake_force_from_hardware(front, rear)` já existe e calcula:

```
clamp   = P_line × A_piston × n_pistons
torque  = 2 × μ_pad × clamp × R_disc_efetivo
F_tyre  = torque / R_wheel
```

Faltam os 6 números por eixo (dianteiro e traseiro podem diferir):

| Parâmetro | Símbolo | Unidade | O que buscar |
|---|---|---|---|
| Nº de pistões da pinça | `n_pistons` | – | pinça de caminhão de corrida (2, 4, 6?) |
| Diâmetro do pistão | `piston_diameter_m` | m | típico 40–70 mm |
| Pressão de linha (pico) | `line_pressure_bar` | bar | freio hidráulico truck racing (80–150 bar?) |
| Coef. atrito pastilha | `pad_friction` | – | pastilha sinterizada/orgânica (0.35–0.55) |
| Raio efetivo do disco | `disc_effective_radius_m` | m | (R_ext+R_int)/2 do disco ventilado |
| Raio de rolamento | `wheel_radius_m` | m | já temos: 0.52 m (295/80 R22.5) |

## Prompt (colar no Perplexity ou Gemini)

```text
Preciso dimensionar o sistema de freio de um caminhão de corrida da categoria
Copa Truck (Brasil, CBA/Vicar, ~5000 kg em ordem de corrida, pneu 295/80 R22.5,
raio de rolamento ~0.52 m). Quero derivar a força de frenagem máxima no contato
do pneu a partir do hardware, não de um número arbitrário.

Para os eixos dianteiro e traseiro, forneça faixas realistas (com fonte) de:
1) número de pistões por pinça e diâmetro do pistão (mm) em caminhões de corrida
   ou trucks pesados de competição;
2) pressão hidráulica de linha de pico (bar) num sistema de freio a disco de
   competição para veículo pesado;
3) coeficiente de atrito de pastilha (sinterizada vs orgânica de competição);
4) raio efetivo (mm) de disco de freio ventilado usado nessa faixa de veículo;
5) se o regulamento Copa Truck 2024-2026 especifica/limita algum desses itens
   (material do disco, diâmetro, pinça monobloco etc.).

Além disso: qual desaceleração longitudinal (m/s² e em g) é realista/observada
em telemetria de caminhões de corrida pesados? (para sanity-check do resultado).

Responda com: tabela dianteiro/traseiro, faixa min-típico-max por item, ≥2 fontes
por afirmação técnica, e destaque o que é medido vs estimado.
```

## Ao receber os dados

1. Colar resultado bruto aqui em `docs/research/` (arquivo datado).
2. Cross-check ≥2 fontes por número.
3. Vitor aprova os valores → preencher `BrakeHardware(front)`/`BrakeHardware(rear)`.
4. Wire opcional em `to_solver_dict`: se hardware presente, `max_brake_force =
   brake_force_from_hardware(...)`; senão mantém o valor atual (back-compat).
5. Rodar solver, reportar Δ lap Cascavel/Interlagos ANTES de commitar (guardrail).
6. Validar contra desaceleração real de telemetria (item do prompt).
