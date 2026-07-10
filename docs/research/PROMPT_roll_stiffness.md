# Prompt de pesquisa — rigidez de rolagem (k_roll) Copa Truck

> **Regra**: Vitor roda no Gemini/Perplexity (deep research). Agente só preparou.
> **Objetivo**: substituir `k_roll_front/rear = 115.000 Nm/rad` (SEM FONTE, herdado
> de carro) por valores de caminhão de corrida, validando o canal de roll derivado.

## Por que importa (contexto de acurácia)

O sim deriva o roll de cabine quasi-estático: `φ = m·a_lat·h_cg / (k_roll_f + k_roll_r)`.
Com os parâmetros atuais (m=4950 kg, h_cg=1.1 m, k_total=230.000 Nm/rad) o pico dá
**18.8° a 1.41 g** → **13.3°/g**. Um veículo de competição rígido opera tipicamente
em ~0.5–2.5°/g. Ou k_roll está ~5–10× mole demais, ou h_cg/braço de rolagem está
errado — provavelmente o k, que veio de preset de carro.

O mesmo k_roll_f/k_roll_r define a **distribuição de transferência lateral (RSD)**
no solver (`frac_f = k_f/(k_f+k_r)`) → afeta o canal handling_balance (under/oversteer)
e, no futuro 3DOF, o balanço dinâmico. A RAZÃO f/r importa tanto quanto o total.

## Veículo (para ancorar a pesquisa)

- Copa Truck (CBA, Brasil): cavalo-mecânico de corrida, **4.800–5.300 kg** em ordem
  de corrida, h_cg ≈ 1.0–1.2 m, bitola ~2.15 m, largura máx 2.465 m (CBA Fig. 14).
- Suspensão típica: eixo rígido com **feixes de mola (leaf springs)** ou molas
  helicoidais adaptadas + **barras estabilizadoras** (ARB) dianteira e traseira;
  amortecedores de competição. Pneu 295/80 R22.5 (~95–125 psi).
- Categorias análogas úteis: **ETRC** (European Truck Racing Championship, MAN/Iveco
  ~5.3 t), NASCAR trucks NÃO servem (picape leve).

## Perguntas (todas com ≥2 fontes; citar unidade e condição)

1. **Roll gradient típico** (°/g) de caminhão de corrida (Copa Truck/ETRC) em regime
   permanente — onboard, imprensa técnica, papers, manuais de equipe. Faixa aceitável?
2. **Rigidez de rolagem total** (Nm/rad ou Nm/°) por eixo ou total: valores medidos ou
   projetados p/ truck racing (feixe + ARB). Alternativa aceitável: rigidez do feixe
   (N/mm por mola × bitola²/2) + contribuição da ARB p/ eu derivar.
3. **Distribuição front/rear** (RSD) usual em truck racing — mais rígido na frente
   (understeer de segurança) ou balanceado? Números, não opinião.
4. **Contribuição do pneu** (295/80 R22.5 a ~110 psi): rigidez vertical do pneu
   (N/mm) — em eixo rígido o pneu é mole em série com a mola e pode dominar o roll.
5. Se houver: h_roll center de eixo rígido com feixe (altura do centro de rolagem),
   pra corrigir o braço (h_cg − h_rc) na fórmula.

## Formato de resposta desejado

Tabela: parâmetro | valor/faixa | unidade | fonte | veículo/condição.
Resultado vai para `data/vehicle_models.json` (k_roll_front/rear) + validação do
canal de roll vs onboard (alvo: φ simulado ≈ real dentro de ~30%).
