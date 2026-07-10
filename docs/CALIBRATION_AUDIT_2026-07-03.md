# Auditoria de calibração dos presets — 2026-07-03

> **⚠️ PARCIALMENTE SUPERSEDED (2026-07-10)** — working tree/opção A-B: resolvido (preset único fundido). Pesquisas: P7 freio ✅ · pista ✅ (doc Validação) · P3 aero parcial (Cx 0.74 do .xrk; falta A_front/Cl) · **P4 µ, P1 governador, P2 massa/CG/Iz, P5 ratios por equipe, P6 curvas torque = ABERTOS**. Estado vivo: SPM §0.

> Contexto: sprint de validação paga (Pérez). Auditoria de `data/vehicle_models.json`
> (working tree, editado 2026-07-02 21:04, **não commitado**) contra
> `docs/COPA_TRUCK_POWERTRAIN_RESEARCH.md`, regulamento CBA 2025/2026 e lap times
> reais da temporada 2025.
> Classificação de confiança herdada do dossiê: 🟢 regulamentar · 🟡 plausível · 🔴 sem fonte.

## 1. Resumo executivo

1. **A edição de 2026-07-02 21:04 (sessão paralela, não commitada) quebrou a calibração.**
   Ela migrou corretamente a transmissão para ZF 6M + r_wheel 0.52 + diff 3.42 (plano do
   dossiê §6), mas **colou o mesmo bloco de parâmetros de carro GT nos 4 presets**
   (h_cg 0.68 m, A_front 4.8 m², Cl −0.5, Iz 7000, wheelbase 3.0 m) e **afrouxou os testes**
   para o resultado passar (assert Cascavel 76–82 s → 70–82 s; baselines regeneradas).
2. **Lap times atuais (working tree):** Cascavel 1:13.3–1:14.5 = **5–6 s mais rápido que a
   pole real (1:19.505)**. No HEAD (antes da edição), o VW fazia 1:19.591 (Δ +0.086 s).
3. **Os 125 testes passando não validam física** — a suíte compara contra baselines
   regeneradas com os próprios valores errados.
4. **Nenhum preset passa no validador de regulamento** (massa < 4950 kg, wheelbase
   3.0 m < 3.25 m, largura externa 2865 mm > 2465 mm).
5. Interlagos tem gargalo adicional independente de veículo: centerline com ruído de
   spline adiciona ~+4 s (LTS_RESEARCH §5). Validar Interlagos só após recaptura do traçado.

## 2. Lap times — sim vs real (medidos hoje)

| Pista | Pole PRO 2025 (real) | Sim HEAD (12M, pré-edição) | Sim working tree (6M + params carro) |
|---|---|---|---|
| Cascavel | **1:19.505** (Beto Monteiro) | VW 1:19.591 (**Δ +0.086 s**) · Scania 1:19.293 · Volvo 1:17.934 | VW 1:14.368 (**Δ −5.14 s**) · Scania 1:14.512 · Volvo 1:13.305 |
| Interlagos | **2:03.905** (Totti, Super Final) | VW 2:11.543 (Δ +7.64 s) | VW 2:06.268 (Δ +2.36 s) · Volvo 2:04.343 |

Leitura honesta: o Δ pequeno de Interlagos no working tree é **cancelamento de erros**
(aero de carro compensa traçado ruidoso), não calibração. A única âncora confiável do
projeto era Cascavel no HEAD — e a edição de ontem a destruiu.

Nota de referência: "1:14–1:20" é o range de **Cascavel**; Copa Truck em Interlagos gira
em ~2:04–2:07 (poles 2025 documentadas no dossiê §0.1).

## 3. Auditoria parâmetro a parâmetro (estado atual do working tree)

Presets `volkswagen_31320` / `scania_r480` / `volvo_fh16` (valores agora idênticos entre
si nos campos de chassi — evidência de copy-paste em massa):

| Parâmetro | Valor atual | Veredito | Fonte / ação |
|---|---|---|---|
| `m` 4500–4600 kg | ❌ viola CBA | Mín. 4890 (2025) / **4950 kg** (2026) com piloto (Art. 21.2 🟢). Corrigir para 4950. |
| `lf`/`lr` 1.2/1.8 (wb 3.0 m) | ❌ viola CBA | Entre-eixos regulamentar 3.30–3.80 m ±50 mm 🟢. HEAD (4.4–4.7 m) também violava. Usar wb real do caminhão (pesquisa) + split por pesagem. |
| `h_cg` 0.68 m | ❌ valor de carro | Sem fonte p/ caminhão. Ordem esperada ~1.0–1.2 m. **Pesquisa P2.** |
| `Iz` 7000 kg·m² | ❌ valor de carro | 4.5 t num chassi >5 m → ordem 12k–20k. HEAD usava 15000 (mais crível, mas 🔴). **Pesquisa P2.** |
| `A_front` 4.8 m² | ❌ valor de carro | Cabine ~2.5 m larg × ~2.9 m alt → 7–9 m². HEAD usava 8.6–8.9 (crível, 🔴 sem fonte). **Pesquisa P3.** |
| `Cl` −0.5 | ❌ downforce de GT | Caminhão de corrida: Cl ~0 a levemente positivo, salvo aero kit. HEAD: +0.03/+0.08. **Pesquisa P3.** |
| `Cx` 0.7 | 🔴 plausível | Faixa caminhão racing 0.6–0.8. **Pesquisa P3.** |
| `mu` 1.58–1.63 | 🔴 suspeito de alto | Pneu truck-racing 22.5" dificilmente > ~1.3. É o principal knob que hoje compensa outros erros. Calibrar com telemetria .xrk; **Pesquisa P4** dá bounds. |
| `r_wheel` 0.52 m | ✅ | 295/80 R22.5 → D≈1.04 m 🟢 (dossiê §4). Ganho real da edição de ontem. |
| `n_gears`/`gear_ratios` 6M (6.75…0.78) | ✅ estrutura / 🟡 valores | Art. 15 = ZF/Eaton 6M 🟢; ratios são os "típicos" do dossiê §3 🟡. **Pesquisa P5** confirma por equipe. |
| `final_drive` 3.42 | 🟡 | Meritor MS-145/147 tático ~3.42 (dossiê §3). **Pesquisa P5.** |
| `P_max` 850–900 kW | ✅ faixa / 🔴 exato | Regulamento: 1000–1250 cv 🟢. Valor exato por marca sem fonte. |
| `T_max` 4200–4500 N·m | ✅ faixa / 🔴 exato | Faixa 3000–5500 🟢. |
| `torque_curve_*` | 🔴 | Estimativas de LLM (dossiê §2 marca explicitamente). **Pesquisa P6.** |
| `rpm_max` 3400–3500 | 🟡 | Coerente com paradigma MB OM 460 (§2). |
| `max_decel` 9.0–9.4 m/s² | 🔴 | ~0.95 g coerente só se µ≈1.6. Se µ real ~1.2, impossível. Amarrar com µ na calibração. **Pesquisa P7.** |
| `max_brake_force` 60–62 kN · `brake_balance` 60 | 🔴 | Sem fonte; calibrar com .xrk. |
| `Cf`/`Cr` 190k/230k N/rad | 🔴 | Sem fonte; impacto baixo no QSS ponto-massa (yaw cap). Prioridade baixa. |
| Diferenciação Scania/Volvo (±kW, ±µ) | ❌ ficção | Copa Truck equaliza desempenho (pop-off por evento). Nomes "R480"/"FH16" são de caminhão de rua. Manter 1 preset genérico calibrado + variações só com dado real. |
| Governador 200 km/h (hardcode `lap_time_solver.py:311`) | 🔴 contraditório | LTS_RESEARCH trata como regulamento; dossiê §1 cita >230 km/h projetado e radar ~160 contraditório. **Pesquisa P1.** Vmax simulada hoje CRAVA em 200 nas 2 pistas → parâmetro dominante. |

`vw_31320_copa_truck_racing_copy_correto`: era o único compliant (wb 3.65 m, m 4950);
a edição de ontem sobrescreveu lf/lr/h_cg/Iz com o bloco de carro e agora **também falha**
no validador (wb 3.0 m).

## 4. Recomendação de correção (decisão do Vitor)

A edição de ontem misturou 1 acerto estrutural (drivetrain ZF 6M real) com contaminação
de chassi/aero de carro e testes afrouxados. Opções:

- **A (recomendada)** — `git restore data/vehicle_models.json tests/` (volta HEAD: Cascavel
  Δ+0.086 s, âncora restaurada). Criar preset experimental `vw_31320_zf6_reference` com o
  drivetrain novo (6M + 0.52 + 3.42) + chassi de caminhão corrigido, e recalibrar µ/torque/aero
  contra Cascavel — exatamente o plano do dossiê §6 (etapa 3). Promover aos presets oficiais
  só depois de validado.
- **B** — manter working tree e corrigir em cima (h_cg, A_front, Cl, Iz, wb, m) + recalibrar.
  Mais rápido, porém perde o baseline limpo e mantém histórico de teste afrouxado.

Em ambas: reverter o assert 70–82 s para 76–82 s (teste nunca deveria ter sido afrouxado).

## 5. Prompts de pesquisa — Vitor executa no Perplexity/Gemini

> Regra: agente prepara, Vitor roda. Exigir **≥2 fontes independentes por afirmação**;
> colar resultados em `docs/research/` e só então promover valores aos presets.
> ETRC (European Truck Racing Championship) é o análogo técnico mais bem documentado —
> usar como proxy quando não houver dado Copa Truck, marcando a origem.

### P1 — Limitador de velocidade (bloqueia Vmax; maior impacto no lap time)

```text
Copa Truck (Brasil, 2024-2026): existe limite eletrônico de velocidade máxima imposto
pelo regulamento técnico ou esportivo (CBA)? Qual o valor exato em km/h e como é
imposto (limitador de rotação, pop-off, radar com punição esportiva)?
Contexto: a Fórmula Truck historicamente limitava em 160 km/h; encontrei menções
contraditórias de 160, 190 e 200 km/h para a Copa Truck atual, e projeções de
velocidade livre >230 km/h. Preciso do valor vigente em 2025-2026.
Responda com: valor + mecanismo + artigo do regulamento + 2 fontes independentes
(regulamento CBA, notícia técnica, entrevista de equipe, onboard com telemetria).
```

### P2 — Massa, CG e inércia do caminhão de corrida

```text
Caminhão de corrida estilo Copa Truck / ETRC (cabine semi-truck, ~4.5-5.0 t, motor
diesel 13L dianteiro): preciso de 3 grandezas físicas com fonte:
(1) Altura do centro de gravidade (h_cg) típica em metros — chassi rebaixado de
    competição, não caminhão de rua;
(2) Momento de inércia de guinada (Iz, kg·m²) — medido ou estimado por distribuição
    de massa (aceito paper SAE/dissertação com metodologia);
(3) Distribuição de peso dianteira/traseira típica em ordem de corrida.
Contexto Copa Truck: peso mínimo 4950 kg com piloto (CBA 2026), entre-eixos
3.30-3.80 m. Se não houver dado Copa Truck, use ETRC (MAN/Iveco/Buggyra) e papers
de truck racing. 2 fontes por grandeza; se estimativa, mostre o cálculo.
```

### P3 — Aerodinâmica (Cx, área frontal, lift/downforce)

```text
Aerodinâmica de caminhão de corrida (Copa Truck brasileiro e ETRC europeu, 2020-2026):
(1) Coeficiente de arrasto (Cd/Cx) típico do caminhão de competição com kit aero
    (defletores, splitter, teto rebaixado) — não caminhão de rua;
(2) Área frontal efetiva em m² (largura máx 2.45-2.55 m, altura de cabine de corrida);
(3) O caminhão gera downforce ou lift? Coeficiente de sustentação (Cl) estimado com
    splitter dianteiro e defletor de teto.
Aceito: papers CFD de truck racing, dados Buggyra/MAN/Iveco ETRC, dissertações.
2 fontes por item; se faixa, dê a faixa e o valor mais provável.
```

### P4 — Pneu: atrito efetivo e raio dinâmico

```text
Pneu de truck racing 22.5" (Copa Truck usa spec por evento definida pela Promotora;
ETRC usa Goodyear 315/70 R22.5 de competição):
(1) Coeficiente de atrito lateral/longitudinal efetivo de pico em pista seca —
    literatura, telemetria publicada ou papers (comparar com slick de carro ~1.4-1.6
    e pneu de rua ~0.9);
(2) Raio dinâmico/rolamento do 295/80 R22.5 e do 315/70 R22.5 sob carga de corrida;
(3) Pressões operacionais típicas a quente no truck racing.
2 fontes por item. Preciso de bounds realistas de µ para calibração (suspeito que
µ=1.6 no meu modelo está compensando outros erros).
```

### P5 — Transmissão e diferencial reais das equipes

```text
Copa Truck 2024-2026: quais caixas de câmbio as equipes usam de fato (regulamento
Art. 15 permite livre com 6 marchas manuais H — ZF 6S 1000 TO, ZF 6S 1700,
Eaton FS-6306/6406A?) e quais as relações de marcha exatas dessas caixas?
Diferencial obrigatório Meritor MS-145/147: quais relações de coroa/pinhão as
equipes escolhem por pista (curta tipo Cascavel vs longa tipo Interlagos)?
Fontes: catálogos ZF/Eaton/Meritor (relações oficiais das caixas citadas),
entrevistas de equipe, regulamento CBA. 2 fontes por caixa.
```

### P6 — Motor: curvas de torque reais

```text
Motores da Copa Truck 2024-2026 (diesel 13L, limite 1250 cv com pop-off lacrada):
quais motores cada marca usa (MWM? Cummins? MAN D28? Scania DC13? Volvo D13?) e
existe curva de torque/potência publicada (dyno, imprensa técnica, equipe)?
Preciso de: torque de pico (N·m e rpm), potência de pico (cv e rpm), rotação de
corte, e o formato da curva (flat entre X e Y rpm?).
Se não houver dado Copa Truck, curvas do ETRC (Buggyra publica dados do D28) servem
como paradigma. 2 fontes por motor.
```

### P7 — Frenagem: desaceleração real

```text
Truck racing (Copa Truck/ETRC): qual a desaceleração máxima típica em frenagem forte
(m/s² ou g)? ETRC usa discos ventilados com refrigeração a água e freia de 160 a 60
km/h em distâncias publicadas — há telemetria ou dados de imprensa?
Contexto: meu modelo usa 9.0-9.4 m/s² (~0.95 g), que parece alto para 4.5-5 t;
preciso de valor real p/ validar ou corrigir, junto com o típico ponto de frenagem.
2 fontes independentes.
```

## 6. Critério de "calibrado" (gate da sprint)

1. Preset único VW com **params estruturais 🟢/🟡** (massa, wb, drivetrain, pneu, limitador)
   e **knobs calibrados** (µ, escala torque, aero) via `scripts/calibrate_vehicle.py` contra
   telemetria .xrk (pipeline LTS_RESEARCH §3).
2. Cascavel: |Δ| ≤ 0.5 s da pole PRO **e** traço de velocidade RMSE baixo (não só lap time).
3. Interlagos: só após recaptura do centerline (senão o traçado domina o erro).
4. Validador de regulamento: `compliant=True` na temporada 2026.
5. Testes de física com janelas **originais** (76–82 s Cascavel), nunca afrouxadas.
