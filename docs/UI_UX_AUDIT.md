# UI/UX Audit — LTS Copa Truck

> Autor: Claude (Opus 4.7) — 2026-07-05
> Branch: `feature/claude-product-upgrade`
> Escopo: apenas front-end Streamlit (`src/visualization/**`).
> Referências mentais: MoTeC i2 Pro, Pi Toolbox, Canopy Simulation, WinTAX.

## 0. Sumário executivo

O app tem substrato técnico maduro (solver two-pass, 143 testes verdes, cache
de solver, histórico persistido, exportadores PDF/HTML), mas a camada visual
delatava protótipo em vários lugares: mistura PT-BR/EN, emojis pesados em
headers e mensagens, ausência de tema, cores Plotly padrão em fundo branco.
Esta primeira passada instalou um tema *dark race-engineering* consistente e
uniformizou tipografia/copy de headers, warnings e botões sem tocar em
lógica de negócio. Todos os 143 testes seguem verdes.

O que sobrou (backlog P1/P2/P3) exige mudança de fluxo, componentização mais
profunda e um refactor no `results.py` (624 linhas, dashboard-monólito) —
riscos que não caberiam antes de quarta sem quebrar testes ou piorar a
experiência atual.

## 1. Tema (aplicado)

Arquivo: `.streamlit/config.toml`.

### 1.1 Paleta (HSL → hex)

| Slot | HSL | Hex | Uso |
|---|---|---|---|
| Background primary | `220 15% 8%` | `#11141a` | Corpo do app |
| Background secondary | `220 12% 12%` | `#1a1d24` | Sidebar, cards, expanders |
| Text primary | `220 15% 92%` | `#e6e8ee` | Corpo |
| Text secondary / caption | `220 10% 65%` | `#9ba1ad` | (herdado do Streamlit dark) |
| **Accent (primary)** | `28 90% 55%` | `#f28a1f` | Botões primários, tabs ativas, checkbox on |

### 1.2 Justificativa do accent

Considerei três candidatos:

- **Laranja motorsport `hsl(28 90% 55%)` (escolhido).** Alta cromaticidade
  sem cair em neon; contraste 7.2:1 no fundo primário (WCAG AAA para texto
  grande, AA para corpo). Semanticamente neutro contra as escalas
  `RdYlGn_r` usadas em heatmaps de sensibilidade (verde = rápido, vermelho
  = lento) — se o accent fosse verde ou vermelho, competiria com essa
  leitura. Coerente com a identidade visual da própria categoria Copa
  Truck (livery amarelo/laranja frequente).
- **Verde telemetria `hsl(150 60% 45%)`.** Bonito mas conflita com o
  significado "OK / rápido" em plots. Rejeitado.
- **Ciano azul-claro `hsl(200 90% 60%)`.** Muito "AI dashboard", pouca
  personalidade de marca. Rejeitado.

Trocar o accent no futuro é uma linha em `.streamlit/config.toml` — a
paleta orbital continua válida.

### 1.3 Base e tipografia

- `base = "dark"` — herda os defaults dark do Streamlit e sobrescreve só o
  que interessa.
- `font = "sans-serif"` — a stack nativa do Streamlit (Source Sans / Inter
  system-loaded) já é moderna e consistente com dashboards de engenharia
  (Grafana, Datadog). Zero webfont extra = zero jank de FOUT.
- `toolbarMode = "minimal"` remove o menu de deploy/report da toolbar,
  reduzindo ruído visual pra cliente pagante.

### 1.4 O que o tema **não** cobre

- Cores de linhas Plotly: continuam como `royalblue`, `tomato`, `seagreen`
  etc. hardcoded. Streamlit ≥1.30 injeta um template `streamlit` no Plotly
  respeitando o `config.toml`, então o *chrome* dos plots (grid, axis,
  paper bg) já fica dark. **P1** abaixo trata da uniformização das cores
  de trace pra uma paleta coerente.
- Componentes de tabela/data_editor herdam o dark nativo automaticamente.

## 2. Página a página

### 2.1 Sidebar (interface.py)

**Antes:**
- Título `LapTimeSimulator`, caption `Copa Truck`.
- Botão global "Run Simulation" com warnings `⚠️`.
- Sem footer de marca.

**Depois (aplicado):**
- Título `LTS Copa Truck` + caption `Lap Time Simulator · SARU Dynamics`.
- Divisórias antes/depois do nav; run block com heading próprio
  `Run simulation`.
- Warnings viraram `st.info` (não é erro do usuário, é pré-condição).
- Footer discreto `© SARU Dynamics · LTS Copa Truck` (atende à regra de
  marca sutil).

### 2.2 Parameters (vehicle_params.py)

**Bom:**
- Duas colunas Setup vs Design é a divisão certa (mental model do race engineer).
- `st.metric` no topo pra Manufacturer/Year/Power/Weight — decisão correta
  copiada de dashboards de telemetria pro.
- Regulation validator já dá feedback pré-save.
- Painel `Save as New Model` bem isolado num expander.

**Traía protótipo:**
- Header `"Vehicle Parameters and Setup"` sem hierarquia (parecia label).
- Faltava caption explicando *o que* essa página faz para um piloto que
  abre pela primeira vez.
- Botão "Save Truck Setup" com label longo e verboso.

**Mudanças aplicadas:**
- Header `Vehicle Parameters` + caption `Configure design specs and race
  setup — save to arm the simulation.`
- O resto ficou preservado (torque curve editor é excelente).

### 2.3 Track (track.py)

**Bom:**
- Radio horizontal para track source (Interlagos vs HDF5) é claro.
- Plot Plotly com boundaries + centerline é o padrão MoTeC.
- Persistência em `tracks/custom/` sem sobrescrever original é higienicamente correto.

**Traía protótipo:**
- Header com emoji 🗺️.
- **Mistura de idiomas grosseira**: warnings/success em PT-BR
  (`"Alterações não salvas na pista!"`, `"Configuração de pista salva com
  sucesso!"`) num app em inglês. É o pior "AI slop" possível pra cliente
  internacional ou piloto que valoriza precisão.
- `st.success` final concatenando três informações num texto único quando
  deveriam ser métricas separadas.

**Mudanças aplicadas:**
- Header `Track` + caption em EN.
- Todos os textos convertidos pra EN.
- Warning de "unsaved changes" mantido, mas com copy sóbrio; o "info" de
  configuração armada virou `st.caption` (menor peso visual).
- Success final substituído por 3 `st.metric` (Circuit / Length / Grip
  factor) — leitura instantânea, alinhada com MoTeC.

### 2.4 Simulation (simulation.py)

**Bom:**
- Tabs Single vs Sweep separam workflows.
- Radio Qualifying vs Standing Start é o modelo mental correto.
- Progress bar por item durante o sweep.

**Traía protótipo:**
- Header `"▶️ Run Simulation"` (emoji + verbo + substantivo).
- `st.info(f"✓ Track Loaded: **{...}** | Vehicle Mode: **{mode}** ({vp.name})")`
  compactando três dados num texto rico — dashboards profissionais usam
  chips/metrics separados.
- Sweep tab tinha subheader `🛠️ Setup Parameter Sweep`.

**Mudanças aplicadas:**
- Header `Simulation` + caption sóbria.
- Info compacto virou 2 `st.metric` (Track / Vehicle com category no help).
- Tab labels curtos (`Single run` / `Parameter sweep`).
- Botões `Run simulation`, `Clear results history` sem emoji.
- Mensagens de progresso/success no formato `label: value · label: value`
  (padrão MoTeC status bar).

### 2.5 Batch Simulation (batch_run.py)

**Bom:**
- Checkbox force re-run com help contextualizando cache é sinal de UI
  madura.
- Passos numerados (1. Select Vehicles, 2. Simulation Mode) guiam bem.

**Traía protótipo:**
- Header `📊 Batch Simulation`, subheaders com emojis.
- Coluna `Source` com string `"cache ⚡"` (impossível de sortar/filtrar).
- Success final verbose (`✅ Batch simulation completed in 3.42s! Winner:
  **VW 31320** with lap time of **1:24.512**.`).

**Mudanças aplicadas:**
- Header `Batch simulation` + caption.
- Track em `st.metric` no topo.
- Success curto (`Batch complete in 3.42 s. Fastest: VW 31320 — 1:24.512.`).
- `"cache ⚡"` → `"cache"`.

### 2.6 Results (results.py — 624 linhas, o monstro)

**Bom:**
- KPIs num grid 4×3 é o layout certo.
- Speed map, GGV diagram, brake trace, fuel flow, sector timing — cobertura
  completa de canais de telemetria.
- Simulation history em expander com filtros (persistência PostgreSQL/JSON).
- Três exportadores (CSV, PDF, HTML) em uma linha.

**Traía protótipo:**
- Header `🏁 Results & Telemetry Dashboard`.
- **Cada subheader com emoji diferente** (🏁 KPIs, 📥 Export, 🗺️ Speed Map,
  📈 Dynamics, 🛑 Brake, 🎮 Driver Inputs, 🏁 Sector) — cacofonia visual.
- Botões download com `📥 Download Telemetry CSV`, `📄 Download PDF
  Executive Report` — redundante (Streamlit já mostra ícone de download).
- 15+ figuras Plotly com estilos hardcoded (`color='royalblue'`,
  `color='tomato'`) e alturas 280/500 misturadas — sem grade coerente.
- Sem separação visual entre "página cheia" vs "cards de canal".

**Mudanças aplicadas:**
- Header `Results` + caption.
- Removidos todos os emojis em subheaders (`Performance KPIs`, `Export
  deliverables`, `Speed map`, `Dynamics channels`, `Brake trace analysis`,
  `Driver inputs`, `Sector timing`).
- Labels de botões enxutos.
- Simulation history expander renomeado `Simulation history` (sem 📚).

**NÃO aplicado (foi pro backlog):** consolidação da grade de plots, paleta
Plotly unificada, agrupamento por acordeão (KPIs / Overview / Dynamics /
Driver / Sectors) — ver P1-01.

### 2.7 Telemetry Overlay (overlay.py)

**Bom:**
- Lap picker automático quando o arquivo tem múltiplas voltas (fastest
  pre-selected) — excelente UX.
- Aceita .xrk (AiM) e CSV com aliases — flexibilidade real.
- Métricas Δt e RMSE já são a linguagem certa (MoTeC "delta report").
- Tabela "Largest divergences" é ouro para o cliente.

**Traía protótipo:**
- Header `📡 Telemetry Overlay — Sim vs Real`.
- Warning `⚠️ Run a simulation first (Simulation tab).`
- Cores de trace hardcoded (`silver`, `royalblue`, `tomato`, `seagreen`).

**Mudanças aplicadas:**
- Header `Telemetry overlay` + caption.
- Warning limpo.
- Cores dos traces **não** alteradas (evitei mexer em plots antes do
  P1-02).

### 2.8 Compare (compare.py)

**Bom:**
- Aceita múltiplos uploads simultâneos.
- Top-3 setups num grid de colunas é elegante.
- Iteração por canal (speed, g_long, g_lat, throttle, brake, steering, tyre
  temp) é sistemática.

**Traía protótipo:**
- Header `📊 Compare Telemetry — CSV Overlay`.
- `st.success(f"⚡ Converted **{uf.name}** | Driver: ...")` com emoji em
  mensagem de sistema.
- Copy pt-BR ausente aqui — bom.

**Mudanças aplicadas:**
- Header `Compare telemetry`.
- Mensagens sistema sem emoji, formato `key value · key value`.

### 2.9 Optimization (optimization.py)

**Bom:**
- Dois otimizadores (Grid Search + Differential Evolution) com radio.
- Progress bar de gerações mostrando best-so-far é padrão pro-tool.
- Heatmap por wing position — hardcore mas correto.

**Traía protótipo:**
- Header `🔧 Setup Optimization`.
- Botões `🧬 Run Differential Evolution`, `🚀 Run Setup Optimization
  Grid-Search` (verbo composto + emoji).
- Subheader `🏆 Top 10 Fast Setups`.

**Mudanças aplicadas:**
- Header + caption.
- Botões curtos (`Run differential evolution`, `Run grid search`).
- Subheaders limpos.

## 3. Arquivos alterados

Total: **10 arquivos** (1 novo, 9 editados).

- `.streamlit/config.toml` — novo, tema dark
- `src/visualization/interface.py`
- `src/visualization/components/vehicle_params.py`
- `src/visualization/components/track.py`
- `src/visualization/components/simulation.py`
- `src/visualization/components/results.py`
- `src/visualization/components/overlay.py`
- `src/visualization/components/compare.py`
- `src/visualization/components/optimization.py`
- `src/visualization/components/batch_run.py`

Não tocado (fora de escopo): `torque_curve.py` (já usa dual-axis chart
maduro, sem "slop"), `helpers.py` (backend puro).

## 4. Backlog

### P1 — bloqueia sensação de "produto" (2–5 dias)

**P1-01: Refactor `results.py` em accordions coesos** — 2 dias.
O arquivo é 624 linhas listando 15+ gráficos verticalmente. Race engineers
usam UI com "modos de vista" (overview / dynamics / driver / suspension).
Proposta: manter KPIs no topo, colocar tudo o mais em `st.tabs(["Overview",
"Dynamics", "Driver inputs", "Sectors"])`. Sem alterar semântica dos
gráficos.

**P1-02: Paleta Plotly unificada** — 4h.
Criar `src/visualization/theme.py` exportando `PLOT_COLORS =
{"speed": "#e6e8ee", "throttle": "#5fb85f", "brake": "#e5484d",
"lat_g": "#f28a1f", "long_g": "#66a3ff", ...}`. Substituir hardcodes
`royalblue`/`tomato`/`seagreen` nos 6 componentes que fazem plot. Baseline:
[MoTeC channel color palette](https://www.motec.com.au). Deve manter
consistência entre `results.py`, `compare.py`, `overlay.py`, `track.py`,
`torque_curve.py`, `optimization.py`.

**P1-03: Fluxo guiado Parameters → Track → Run** — 1 dia.
Hoje a sidebar deixa o usuário abrir Simulation direto e ver dois warnings.
Ideias:
- Stepper visual na sidebar mostrando estado (verde/vermelho) de
  Parameters e Track.
- Redirecionar rerun após "Save Truck Setup" pra "Track" automaticamente.
- Botão global "Run" nunca some — só fica `disabled=True` com tooltip
  explicando qual pré-condição falta.

**P1-04: Empty states dignos** — 4h.
Overlay/Compare/Optimization/Results, quando abertos sem pré-requisitos,
hoje mostram apenas `st.warning`. Substituir por um bloco centralizado com
ícone + título + CTA (`st.button("Go to Parameters")`) — padrão Linear /
Vercel.

### P2 — polir profissionalismo (1–3 dias)

**P2-01: Simulation runner extraído** — 1 dia.
O bloco "run + persist + append to history" está duplicado em
`interface.py`, `simulation.py` e `batch_run.py`. Extrair pra
`src/visualization/services/run_simulation.py` (SRP: single entrypoint,
retorna `RunResult`). Reduz chance de divergência quando o solver evoluir.

**P2-02: PDF report SARU-branded** — 4h.
O PDF hoje usa navy `#1A365D` e sample styles ReportLab. Alinhar com a
paleta dark: logo/marca "SARU Dynamics" no topo, footer com laranja
motorsport como accent. Manter conteúdo (KPIs, sector table, speed trace
Matplotlib). Arquivo: `results.py::generate_pdf_report`.

**P2-03: HTML report interativo com theme injection** — 4h.
Hoje concatena `pio.to_html` sem CSS. Adicionar `<style>` com paleta dark
+ `plotly.graph_objs.layout.Template` custom antes de renderizar cada
figura. Cliente que baixar o HTML ainda vê a marca.

**P2-04: Micro-animações e transições** — 4h.
Streamlit ≥1.32 tem `st.fragment` — usar em Results pra evitar re-render
completo ao mexer no slider "Number of sectors" (hoje re-plota 15+
figuras). Adicionar `duration=` fade em `st.metric` (via CSS mínimo em
markdown) — os race engineers de Pi Toolbox adoram esse detalhe.

**P2-05: Copy consistency EN-only sweep** — 2h.
Fazer varredura final por strings PT-BR residuais em código não-frontend
(exceções, mensagens de log em `helpers.py`, docstrings). Alinha o produto
antes de vitrine pública.

### P3 — refinamentos (1 dia total ou depois de feedback)

**P3-01: Iconografia sutil por página** — 2h.
Se o operador quiser um ícone por página (não emoji), usar `st.image` com
SVG monocromático 20px alinhado ao lado do header. Fonte:
[lucide-react SVG](https://lucide.dev) exportado como PNG/SVG estático.
Sem novas deps.

**P3-02: Reordenar sidebar por freq de uso** — 30min.
Analytics de cliente mostrarão. Proposta inicial: Parameters, Track,
Simulation, Results (juntos), Overlay, Compare, Optimization, Batch (final).

**P3-03: Tooltips com física** — 2h.
Em `Simulation`, adicionar `help=` em cada slider do sweep explicando a
fórmula (ex: `CG height affects load transfer per Δψ = h_cg * a_lat / g`).
Diferencial contra concorrentes (Canopy Simulation).

**P3-04: Density toggle** — 2h.
`st.toggle("Compact view")` que empilha KPIs em 6 colunas em vez de 4 para
usuários com display 4K. Nice-to-have.

**P3-05: SARU landing/hero opcional** — 1 dia (se vira vitrine pública).
Uma home page dedicada com screenshot animado + link "Launch app". Não
prioridade pra demo com cliente pagante, mas essencial se `saru.dev` for
divulgar.

## 5. Validação

```
$ .venv/bin/python -m pytest -q
143 passed in 9.48s
```

Nenhum teste UI (`tests/test_ui_vehicle_params.py`) precisou de ajuste — o
teste consulta widgets por `key=`, e essas keys ficaram intocadas. A regra
"ajuste seu código, nunca o teste" foi respeitada.
