# Session Log — 2026-06-11 — Physics v2 + Architecture + Learning

> **HISTÓRICO (2026-06-11)** — log de sessão preservado. Não reflete o estado atual; ver SPM.md.

> Running log para handoff em caso de limite de sessão. Atualizar a cada merge.

## Decisões de modelagem (aprovadas pelo Vitor)

1. **Solver: QSS aprimorado (quase-estático "3DOF")**, NÃO 10DOF.
   - QSS GGV é o padrão para otimização de setup (Brayshaw & Harrison 2005;
     TUM FTM laptime-simulation). ~30 ms/volta → viabiliza calibração e
     otimização com milhares de iterações.
   - 10/14DOF transiente exige driver model em malha fechada e 100-1000×
     mais custo — papel do **LTS_SARU (14DOF)**, não deste LTS.
   - O gap real não era DOF: era subsistema morto. Física v2 integra motor,
     transmissão, freio e pneu DE VERDADE no solver.
2. **Tudo que está na UI entra na física** (ordem do Vitor: não remover da
   UI; melhorar a física).
3. Arquitetura: solver é o motor físico único; implementações paralelas
   mortas são arquivadas; validação de params ligada na UI.

## Bugs confirmados na auditoria (a corrigir na física v2)

- B1: `max_power` não limita tração (curva VW entrega 1170 kW vs 850
  declarados; fuel usa P clampado → inconsistente).
- B2: `abs(p.Cl)` trata lift como downforce (Cl +1.0 → volta MAIS rápida).
- B3: `v_lat_max = sqrt(mu*g*R)` ignora downforce (inconsistente com o
  círculo de atrito).
- B4: `a_long`/throttle/brake derivados do forward pass, nunca recomputados
  após o backward pass (pico canal −2.9 vs real −9.2 m/s²; corr 0.67).
- B5/B6: presets m=4500 vs UI força ≥4950; µ=1.52 é fator de calibração
  implícito.
- Parâmetros mortos comprovados (Δlap = 0.0000s): Cf, Cr, Pacejka B/C/D/E,
  Iz, transmission_efficiency, shift_time, brake_response_time, abs_*.

## Streams (worktrees paralelas)

| Stream | Branch | Status |
|--------|--------|--------|
| 1. Física v2 (bugs B1-B6 + params vivos + quasi-static load transfer) | `feature/physics-v2` | ✅ MERGED (98 testes) |
| 2. Arquitetura (arquivar mortos, validate no fleet, libxrk, scripts) | `feature/architecture-consolidation` | ✅ MERGED |
| 3. Aprendizado (pesquisa LTS, calibração .xrk, sensibilidade, otimizador DE) | `feature/learning-calibration` | ✅ MERGED (100 testes) |

Ordem de merge: 1 → 2 → 3 (baselines regenerados APENAS no stream 1 e na
consolidação final; streams 2/3 não regeneram).

## Regras invioláveis (inalteradas)

- Janelas de validação são REALIDADE: VW 31320 Cascavel 76–82 s,
  Interlagos 125–132 s — devem passar após recalibração.
- pytest 100% por merge; Conventional Commits; merge --no-ff em develop.

## Pendências pós-merge (executor: sessão principal)

- [x] Baselines regenerados (física v2) com evidência no commit
- [x] Resample de Interlagos AVALIADO E REJEITADO: a spline cúbica em
      862 pts amplifica ruído de curvatura (+4 s/volta) — caminho certo é
      recapturar o centerline dos GPS dos .xrk (ver docs/LTS_RESEARCH.md §5)
- [x] Calibração v2: S_LOAD=0.12, presets mu 1.58-1.63 / Cx 0.68-0.72 /
      bias 60% / ABS on / massa 4500 kg (mínimo regulamentar A CONFIRMAR
      com o Pérez — o piso de 4950 kg da UI era inconsistente e foi alinhado)
- [x] Standing start corrigido: era MAIS RÁPIDO que qualifying (mu sem
      penalidade); agora +7.6 s, fisicamente correto
- [x] CLAUDE.md atualizado
- [x] Relatório final ao Vitor
- [ ] PRÓXIMO: pip install libxrk (local) → converter .xrk → calibração
      cross-track Interlagos↔Cascavel → fator piloto via GG realizado
