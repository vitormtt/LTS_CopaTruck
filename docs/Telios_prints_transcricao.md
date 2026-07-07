# Transcrição de Prints — Telios KPI (2026-07-06)

> Fonte: 11 screenshots de vídeo-demo no LinkedIn do **Telios KPI** (analisador/gerador de
> relatórios KPI para telemetria sim-racing, UI em italiano). Prints em `docs/Telios imagens/`.
> Transcrição refeita em 2026-07-07 por visão direta (a rodada anterior via API Gemini falhou
> com 403 — `GEMINI_API_KEY` ausente). Síntese p/ o ecossistema: `saru-KB/SARU_Arquitetura_Software.md §2.5`.

## 1. Session Setup (17-52-50)
Janela **TELIOS KPI — SESSION SETUP**:
- **Database** (sims suportados): Assetto Corsa · Assetto Corsa Comp. · **iRacing** (selecionado) · Legend Cars · Huracán Supertrofeo.
- **Vehicle Config:** dropdown (ex.: "Legend Cars").
- **Nome Report:** auto-gerado `KPI_Report_20260630_012508`.
- **Opções:** checkbox `KPI PREVIEW`.
- **File di input:** drag-and-drop ou "+ AGGIUNGI FILE".
- Ações: `ANNULLA` / `GENERA KPI →`.
Fluxo: escolhe sim + config de veículo + arquivos de telemetria → gera relatório completo em 1 clique.

## 2. Report Preview — KPI Summary Table (17-53-20, plot 1/47)
Relatório tem **47 plots** navegáveis; render **nativo PyQtGraph** (zoom: scroll, pan: drag) com opções NATIVE/Pan/Zoom/fullscreen. Plot list visível (1–19):
1. KPI Summary Table · 2. Best Lap Overview · 3. Sector Delta Boxplot · 4. Laptime Boxplot per Run · 5. Laptimes per Run · 6. Laptime · 7. Race Average (Sorted Laptimes) · 8. Tyre Pressures per Corner · 9. Tyre Temperatures per Corner · 10. Front Temperature Balance · 11. Left Temperature Balance · 12. Front Pressure Balance · 13. Left Pressure Balance · 14. Throttle Aggression · 15. Throttle Aggression Boxplot · 16. Throttle Release · 17. Full Throttle Time · 18. Steering Smoothness · 19. Steering Speed · (20. Brake Balance…)

**KPI Summary Table** — comparação lado a lado DRIVER A × DRIVER B. Nota metodológica no cabeçalho: *"Laptime/consumo/Pacejka: média robusta (filtro IQR). Roll/Pitch Stiffness: pendenza regressione lineare (ay↔roll, ax↔pitch). Skewness e Kurtosis sull'intero segnale ammortizzatore (Fisher)."*

| KPI | Driver A | Driver B |
|---|---|---|
| **PERFORMANCE** | | |
| Mean Laptime [s] | 93.958 | 92.539 |
| Mean Fuel Cons. [L/lap] | 2.551 | 2.667 |
| Starting Fuel [L] | 46.1 | 36.2 |
| Top Speed [km/h] | 254.3 | 256.9 |
| Mean Ay Max [G] | 2.846 | 2.712 |
| **GRIP FACTORS** | | |
| Mean Overall Grip [G] | 1.363 | 1.379 |
| Mean Cornering Grip [G] | 1.493 | 1.517 |
| Mean Braking Grip [G] | 1.530 | 1.478 |
| Mean Accel Grip [G] | 0.447 | 0.436 |
| **WIND** | | |
| Mean Wind Speed [km/h] | 11.0 | 16.4 |
| Mean Wind Dir. [°] | 4.8 | 4.9 |
| **VEHICLE DYNAMICS** | | |
| Roll Stiffness [deg/G] | 0.251 | 0.254 |
| Pitch Stiffness [deg/G] | 0.054 | 0.055 |
| **DAMPERS** (do PDF, print 17-54-25) | | |
| Skewness FL / FR / RL / RR [-] | −0.614 / 1.028 / −0.300 / 0.993 | −0.432 / 1.165 / −0.272 / 1.114 |
| Kurtosis FL / FR / RL / RR [-] | 33.567 / 36.755 / 38.411 / 43.085 | 36.672 / 48.193 / 46.969 / 56.172 |

## 3. Sector Delta Boxplot (17-53-29, plot 3/47)
"Sector Delta vs Reference": violin+boxplot do delta de tempo [s] **por setor (S1/S2/S3)** de cada volta vs best lap do run (+ = mais lento que a referência). Nota: exige ≥2 runs / delta com ~2 min. Mostra dispersão/consistência por setor (S3 do exemplo: apertado; S1/S2: espalhados).

## 4. Laptimes per Run (17-53-34, plot 5/47)
Tabela crua de voltas por driver. A: Lap1 97.430 → Lap12 106.886 s (out/in laps visíveis: 99.109, 107.395). B: Lap1 93.211 → Lap13 101.123 s. Base dos boxplots (4) e race average (7).

## 5. Tyre Pressures per Corner (17-53-48, plot 8/47)
4 subplots **FL/FR/RL/RR**: pressão [bar] vs nº da volta, A × B sobrepostos — curva de *build-up* (≈1.65 → ≈1.85–1.9 bar estabilizando ao longo do stint). Par com o plot 9 (temperaturas por canto) e balanços 10–13 (frente/esquerda de temp e pressão).

## 6. Export PDF (17-54-25 e 17-54-36)
Relatório exporta **PDF de 47 páginas** (`KPI_Report_20260626_…` aberto no Adobe). Pág. 2 **Best Lap Overview**: overlay speed×distance A (92.30s) × B (91.80s), **delta-time contínuo** no eixo direito, **ganho/perda por trecho destacado** (+0.88s / −0.40s / −0.17s), e traces empilhados no mesmo eixo de distância: steering [deg], brake [%], throttle [%].

## 7. Plots avançados (17-54-52 → 17-55-12)
- **G-G Plot** (pág. 37): Ax×Ay por driver, nuvem colorida por velocidade (0–250 km/h) — envelope de aderência utilizado.
- **Ax vs Pitch** (pág. 41): dispersão + regressão linear, **slope = 0.054 deg/G** = pitch stiffness efetiva (mesma metodologia do KPI da tabela).
- **Polar Grip Factors — All Runs** (pág. 45): radar Cornering / Braking / Acceleration / Combined / Aero, A × B sobrepostos (escala 0.2–1.6 G).
- **Damper Velocity Histograms** (LF/RF/LR/RR): distribuição de velocidade do amortecedor [mm/s, ±200] com **zonas HS REB / LS REB / LS BMP / HS BMP** anotadas em % + skew/kurt por canto, A × B.

## Leitura p/ LTS/SA (resumo)
Telios KPI = **relatório KPI batch de 1 clique** (setup → 47 plots padrão → PDF), persona "engenheiro-lite", com estatística robusta (IQR, Fisher skew/kurt, stiffness por regressão) e comparação A/B nativa. Checklist de features e implicações arquiteturais destiladas em `saru-KB/SARU_Arquitetura_Software.md §2.5`.
