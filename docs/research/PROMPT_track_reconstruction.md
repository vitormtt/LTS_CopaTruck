# Prompt de pesquisa — reconstrução e validação de modelo de pista p/ lap sim

> **Regra**: Vitor roda no Gemini/Perplexity (deep research). Agente só preparou.
> Contexto: LapTimeSimulator_CopaTruck. Precisamos do centerline + larguras de
> Interlagos (e Cascavel) fiéis ao real, e de um método para validar o modelo
> contra telemetria .xrk. Achado: o repo já tem downloader TUM FTM
> (`racetrack-database`, arquivo `SaoPaulo.csv`) com centerline surveyed + larguras
> reais por ponto (4300 m vs real 4309 m). GPS de 1 volta (.xrk) dá a *racing line*
> encolhida (4241 m) + ruído, não a geometria. Objetivo da pesquisa: melhor
> prática para **combinar geometria surveyed + telemetria GNSS multi-volta + tempos
> reais** e otimizar o modelo p/ ficar próximo do real.

## Perguntas (responda cada uma com ≥2 fontes citadas)

1. **Fonte de geometria de pista para lap simulation**: comparação entre (a) bases
   surveyed tipo TUMFTM/racetrack-database e Track Geometry do FIA/AMS, (b) OSM
   Overpass (ways `highway=raceway`), (c) reconstrução por GNSS multi-volta. Qual
   é o padrão em ferramentas sérias (OptimumLap, Canopy, AVL VSM, WinTAX/MoTeC)?
   Precisão típica (m) de cada fonte.

2. **Racing line vs centerline**: uma volta rápida de GPS segue a linha de corrida
   (corta ápices), não o eixo geométrico. Como recuperar o centerline a partir de
   N voltas GNSS (média por *track-fraction* / *s-coordinate*, ajuste de spline
   com regularização de curvatura, uso das bordas)? Quanto a linha de corrida
   encurta o comprimento vs centerline (ordem de grandeza %)?

3. **Alinhamento / georreferenciamento (map-matching)**: métodos para alinhar uma
   nuvem de pontos GNSS (frame ENU local) a um centerline surveyed em outro frame
   (Procrustes / ICP / rigid+scale least-squares). Como reamostrar por
   *arc-length* (coordenada `s`) p/ sobrepor canais (velocidade, Ax/Ay) por
   posição na pista e não por tempo. Ferramentas (frenet, `trajectory_planning_helpers` da TUM).

4. **Largura de pista e boundaries**: como as bordas (`w_tr_left/right`) entram no
   cálculo de racing line de curvatura mínima (método TUM `min-curvature`), e o
   impacto de errar a largura no tempo de volta. Larguras reais de Interlagos e
   Cascavel (m) por trecho, se houver fonte.

5. **Validação do modelo de pista/veículo**: métricas padrão para validar um lap
   sim QSS contra telemetria real — RMSE de velocidade por distância, erro de
   velocidade mínima de curva, delta de setor, top speed, envelope G-G. Tolerâncias
   aceitáveis na indústria. Como separar erro de *pista* de erro de *veículo/µ*.

6. **Centerline vs linha ótima no solver QSS**: rodar o solver seguindo o centerline
   vs uma linha de curvatura mínima muda o tempo de volta. Qual é a convenção em
   lap sims (dirige-se a linha ótima?) e quanto o "piloto perfeito" QSS deve ficar
   abaixo do tempo real de qualifying (margem típica %)?

## Entregável desejado
- Recomendação de pipeline: fonte de geometria → alinhamento GPS → boundaries →
  racing line → calibração µ → validação, com as ferramentas/bibliotecas nomeadas.
- Valores/tolerâncias numéricas p/ os gates de validação (RMSE, delta de setor).
- Resultados em `docs/research/` (resumo + fontes) antes de promover ao código.
