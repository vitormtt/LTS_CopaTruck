# Copa Truck — Dossiê de Powertrain, Transmissão e Pneus (2024–2026)

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
