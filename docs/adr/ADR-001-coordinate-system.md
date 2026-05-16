# ADR-001 — Sistema de Coordenadas

- **Status:** Aprovado
- **Data:** 2026-05-16
- **Repos afetados:** Todos os 5 (global)

## Contexto

O ecossistema SARU Dynamics possui 5 simuladores com origens distintas. Sem uma convenção unificada, vetores de força, slip angles e canais de telemetria têm sinais inconsistentes entre produtos, gerando erros silenciosos na comparação de dados.

## Decisão

**ISO 8855** como convenção global de coordenadas do veículo.

### Definição do frame

| Eixo | Direção | Positivo quando |
|------|---------|----------------|
| x | Longitudinal | Para frente (sentido do movimento) |
| y | Lateral | Para a esquerda |
| z | Vertical | Para cima |

- **Rotações:** regra da mão direita — roll (x), pitch (y), yaw (z)
- **Slip angle α:** positivo quando velocidade lateral é positiva (curva à esquerda)
- **Downforce (Fz aero):** negativo em ISO 8855 (força para baixo = −z)
- **Origem:** centro do eixo dianteiro projetado no solo (documentar exceções)

### Atitude do veículo

- **Interno:** quaternion `q = [qw, qx, qy, qz]`
- **I/O humano-legível:** Euler em graus `[roll, pitch, yaw]`, extraído do quaternion

### Conversões na ingestão de dados

| Fonte | Convenção original | Conversão |
|-------|-------------------|-----------|
| ACC / iRacing | ISO 8855 (nativo) | Nenhuma |
| GT7 / AMS2 | SAE J670 (x frente, y direita, z cima) | y → −y |
| GPS (WGS-84) | ENU (East-North-Up) | Rotacionar para heading do veículo |
| Khalil 2018 (FullVehicleSimulation) | SAE J670 | Migrar na Fase A1 |

### Pacejka MF 5.2

Coeficientes verificados para ISO 8855:
- α positivo → Fy positivo (força lateral para a esquerda)
- κ positivo → Fx positivo (força de tração)
- Recalibrar se coeficientes vindos de fonte SAE.

### Aero map

- Eixos no frame do veículo (ISO 8855)
- ride_height: distância do solo, sempre positivo
- Fz aerodinâmico: negativo = downforce (comprime suspensão)

## Alternativas consideradas

**SAE J670 (x frente, y direita, z cima):**
- Legado — Khalil 2018 e literatura clássica USA usam SAE
- Descartado: ISO 8855 é padrão atual em veículos terrestres, adotado por MoTeC, Cosworth e fornecedores de telemetria modernos

## Consequências

- **FullVehicleSimulation:** Contém código Khalil em SAE J670. Migrar na Fase A1 antes de qualquer integração cross-repo.
- **LapAnalyzer parsers:** Todos os parsers devem traduzir para ISO 8855 antes de persistir.
- **Novos módulos:** Qualquer novo solver, modelo de pneu ou parser deve operar em ISO 8855 nativamente.

## Referências

- ISO 8855:2011 — Road vehicles — Vehicle dynamics and road-holding ability — Vocabulary
- SAE J670e — Vehicle Dynamics Terminology
- Khalil et al. (2018) — "Modeling, Simulation and Validation of 14 DOF" (SAE convention)
- Guiggiani, M. — "The Science of Vehicle Dynamics" (ISO convention)
