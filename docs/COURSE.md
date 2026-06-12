# SARU Course — Ementa do Curso LTS Copa Truck

> **Status**: esqueleto — preencher com Vitor e Pérez

## Visão geral

Curso prático de simulação de tempo de volta usando Python como ferramenta principal.
Produto SARU Course da SARU Dynamics — baseado no simulador LapTimeSimulator_CopaTruck.

---

## Módulos

### Módulo 1 — Fundamentos de simulação de tempo de volta
- O que é um lap time simulator e para que serve
- Diferença entre simulação de ponto de massa e quasi-steady-state
- Visão geral do pipeline: dados → solver → resultado
- Ferramentas: Python, NumPy, SciPy, HDF5, Streamlit

### Módulo 2 — Modelo de veículo (ponto de massa → quasi-steady-state)
- Modelo de bicicleta 2DOF: forças laterais e longitudinais
- Parâmetros de veículo: massa, geometria, aero, transmissão, freios
- Curva de torque diesel e seleção automática de marcha
- Círculo de atrito e limites de tração
- Implementação: `VehicleParams` dataclass

### Módulo 3 — Modelo de pneu
- Fundamentos de dinâmica do pneu: deslizamento lateral e longitudinal
- Modelo linear simplificado (Cf, Cr)
- Magic Formula Pacejka (introdução)
- Implementação: `TireModel` ABC e `LinearTireModel`

### Módulo 4 — Pipeline Python: dados → solver → resultado
- Leitura de circuito em HDF5 (TUM FTM format)
- Forward-Backward Solver (Two-Pass): algoritmo passo a passo
- Forward pass: aceleração máxima por trecho
- Backward pass: frenagem mínima para entrada de curva
- Exportação de resultados (CSV telemetria)

### Módulo 5 — Validação contra telemetria real
- O que é cross-validation em simulação
- Como comparar resultado simulado vs telemetria de corrida
- Métricas: erro de tempo de volta, perfil de velocidade, pontos de frenagem
- Interpretação de divergências e ajuste de parâmetros

### Módulo 6 — Streamlit: dashboard interativo
- Fundamentos de Streamlit: cache, session_state, layout
- Separação lógica de negócio vs interface
- Dashboard: seleção de veículo, configuração de pista, visualização de resultado
- Deploy local e configuração

---

## Pré-requisitos

<!-- TODO: preencher com Vitor -->
- Python intermediário (funções, classes, NumPy básico)
- Conceitos básicos de mecânica clássica
- Interesse em motorsport / engenharia automotiva

## Carga horária

<!-- TODO: preencher com Vitor e Pérez -->
- Total estimado: XX horas
- Formato: XX sessões de X horas

## Materiais

<!-- TODO: preencher -->
- Slides por módulo
- Notebooks Jupyter de exercícios
- Repositório de referência: vitormtt/LapTimeSimulator_CopaTruck
- Referências bibliográficas: Rajamani (Vehicle Dynamics), Pacejka (Tyre and Vehicle Dynamics)
