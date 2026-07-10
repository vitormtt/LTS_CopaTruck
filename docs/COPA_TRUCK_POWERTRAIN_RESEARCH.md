# Copa Truck — Dossiê de Powertrain, Transmissão e Pneus (2024–2026)

> **REFERÊNCIA VIVA (dossiê CBA)** — 2026-07-10: drivetrain ZF6/3.42/0.52 PROMOVIDO ao preset único. Ratios ainda 🟡 (P5 confirma por equipe); torque curve segue estimativa (P6 aberto).

## 0. Regulamento técnico oficial CBA — verificado em 2026-06-12 🟢

PDFs oficiais (cba.org.br/upload/downloads):
`copa-truck-regulamento-tecnico-2025-.pdf` (806) e
`copa-truck-regulamento-tecnico-2026-.pdf` (856).

| Parâmetro | 2025 | 2026 | No simulador |
|---|---|---|---|
| Peso mín. caminhão+piloto (Art. 21.2) | **4 890 kg** | **4 950 kg** | `regulation_validator` por temporada (default 2026) |
| Peso mín. eixo dianteiro s/ piloto (Art. 21.2) | **2 520 kg** | **removido** | check só na temporada 2025 |
| Entre-eixos (suspensão) | 3 300–3 800 mm ±50 | idem | 3.25–3.85 m ✓ |
| Largura máx. no ombro do pneu (Fig. 14) | 2 450 mm +15 | idem | 2.465 m ✓ |
| Cilindrada (Art. 10) | ≤13 000 cm³ (+1,5% → 13 195) | idem | n/a (curvas de torque) |
| Diferencial (Art. 14.10) | Meritor MS-145/147 p/ todas as marcas; lacrado por evento | idem | pendente no preset |
| Câmbio (Art. 15) | **livre**, manual padrão H; vetado automático/automatizado | idem | 12 marchas atuais não violam regra, mas não refletem as ZF/Eaton 6M usadas |
| Pneus (Art. 5) | marca/spec **definidas pela Promotora por evento** (informativo técnico) | idem | medida exata exige informativo/RPP ou Pérez |
| Lastro | proibido (exceto lastro de sucesso da Promotora) | idem | — |

## 0.1 Tempos reais de referência (temporada 2025) 🟢

| Pista | Pole PRO | Pole Elite | Simulador (VW 31320) |
|---|---|---|---|
| Cascavel (jul/2025) | **1:19.505** (Beto Monteiro) | 1:21.208 (Rafa Lopes) | **1:19.455 — Δ 0.05s da pole PRO** ✓ |
| Interlagos (Super Final dez/2025) | **2:03.905** (Totti) | 2:06.680 (Perdoncini) | 2:11.343 — **+5 a +7s lento**: causa conhecida = centerline com ruído de spline (LTS_RESEARCH §5); recapturar dos GPS dos .xrk |
| Goiânia (Super Final 2024) | 1:51.242 (Giaffone) | — | **pista não existe no simulador** — candidata a próxima adição |

> Fonte: pesquisa profunda (Gemini Deep Research) consolidada em 2026-06-12,
> revisada criticamente para uso no simulador. **Cada dado está classificado
> por confiabilidade** — só promova um dado a parâmetro de preset/solver após
> validação com o regulamento CBA oficial e/ou telemetria do Pérez.
>
> Classificação: 🟢 regulamentar (citável) · 🟡 plausível (estimativa
> técnica) · 🔴 estimado por LLM (verificar antes de usar)

## 1. Massa e desempenho global

| Dado | Valor | Conf. | vs. modelo atual |
|---|---|---|---|
| Massa de competição | 4.200–4.900 kg | 🟢 | presets 4500 kg ✓ dentro; validador exige ≥4890 c/ piloto |
| Potência máxima | 1.000–1.250 cv (735–919 kW) | 🟢 | presets 850–900 kW (1156–1224 cv) ✓ |
| Torque máximo | 3.000–5.500 Nm | 🟢 | presets 4200–4400 Nm ✓ |
| Vmax em retas | >230 km/h (projeção 258) | 🟡 | solver limita a 200 km/h ("match qualifying telemetry") — **conflito a revisar com telemetria**; a pesquisa também cita restrição por radar (~160 km/h?) de forma contraditória 🔴 |

## 2. Motores — curvas de torque estimadas 🔴

As tabelas abaixo são **estimativas do LLM** (coerentes com P = T·rpm/7023,5,
mas não medidas). Úteis como ponto de partida de presets experimentais; NÃO
substituem as curvas calibradas dos presets atuais.

**Mercedes-Benz OM 460 (paradigma alta rotação — corte ~3.500 rpm):**
rpm × Nm: 1000:3500 · 1500:4900 · 2000:5500 (pico) · 2500:4750 · 3000:3800 · 3500:2508
(potência estabilizada ~1.250 cv pelo pop-off; pico matemático 1.690 cv @2.500 é cortado)

**FPT Cursor 13 / Iveco (paradigma alto torque — corte ~2.800 rpm):**
rpm × Nm: 1400:4300 (pico) · 1800:4100 · 2200:3870 · 2400:3750 · 2800:3510

Regulamentar associado: 🟢 cilindrada ≤13.000 cm³ (+1,5% retífica), blocos de
linha em ferro fundido, sem internos de titânio/ligas exóticas, injeção
eletrônica obrigatória, válvula Pop-Off lacrada entre compressor e coletor
(calibração definida por evento), telemetria de emissões (NOx/opacidade) com
punição esportiva.

## 3. Transmissão — CONFLITO IMPORTANTE com os presets atuais

🟢 Regulamento (Art. 15): caixa acoplada direta ao motor, troca mecânica em
"H" (vetadas borboletas no volante), **caixas de 6 marchas ZF/Eaton**
(ZF 6S 1000 TO / 6S 1700, Eaton FS-6306/6406A) e diferenciais Meritor
MS-145/147 (frequentemente travados/spool).

🟡 Relações típicas (família ZF Ecomid/Eaton FS):
`6.75 / 3.60 / 2.13 / 1.39 / 1.00 / 0.78` com diferencial tático ~3.42:1
(2.50–2.80 para motores de giro baixo).

**Os presets atuais usam 12 marchas (14.5→0.75, diff 4.0) — perfil de caixa
de RUA (Ecosplit 16M simplificada), não a caixa de corrida.** A física foi
calibrada com essa transmissão nas janelas de telemetria, então a migração
para 6 marchas reais exige recalibração completa (shift map, rpm bands,
arrasto) contra os .xrk. Modelagem de referência da transmissão de rua
(R_total = R_main × R_splitter × R_range) registrada na pesquisa para o
futuro modelo genérico.

## 4. Pneus e pressões — base do `_P_OPT_PSI`

| Dado | Valor | Conf. | vs. modelo atual |
|---|---|---|---|
| Pneu de prova | 295/80 R22.5 (D≈1,04 m → r≈0,52 m) | 🟢 | presets usam r_wheel 0,65–0,67 m — **CONFLITO** (r calibrado junto com a transmissão fictícia; corrigir em conjunto) |
| Pneu no validador de regulamento | 315/70 R22.5 (largura 0,315 m) | 🟡 | `regulation_validator.TYRE_WIDTH_M` — conferir qual é o homologado |
| Pressão regulamentar | **não especificada pela CBA** | 🟢 | — |
| Faixa operacional racing (295/80 R22.5) | ~95–125 psi a frio | 🟡 | solver: `_P_OPT_PSI=110`, `_P_FACTOR_K=1.5e-5` (coupling térmico DESLIGADO até calibrar) |
| Escala de pressão na UI/setup | 1,4–2,4 bar (20–35 psi) | — | escala de CARRO — migrar UI + presets + apply_setup juntos quando o coupling for calibrado |

## 5. Hibridização (VW Meteor Mission Zero) — roadmap

🟢 Motor elétrico AC ≤100 kW (+136 cv), +580 Nm no virabrequim, KERS na
frenagem; uso pleno restrito aos treinos livres. Relevante para um futuro
modo híbrido no solver (torque elétrico instantâneo a 0 rpm preenchendo o
turbo lag) — sem impacto no modelo atual.

## 6. Plano de adoção no simulador

1. **Curto prazo (feito):** `_P_OPT_PSI/_P_FACTOR_K` na escala de caminhão
   (coupling off); este dossiê como referência rastreável.
2. **Com o regulamento CBA em mãos:** confirmar pneu homologado
   (295/80 vs 315/70) e atualizar `regulation_validator`.
3. **Com telemetria (.xrk):** calibrar r_wheel real + transmissão ZF 6S +
   diff Meritor num preset experimental (`*_zf6_reference`), validar contra
   as janelas e só então promover aos presets oficiais.
4. **Histórico de simulações (feito):** todos os runs persistem em
   `simulation_results` — usar a comparação corrida-a-corrida para medir o
   efeito de cada etapa de calibração.
