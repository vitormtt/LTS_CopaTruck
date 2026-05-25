---
name: tdd
description: Red-Green-Refactor workflow para features novas. Acionar sempre que criar feature com comportamento observável.
---
## Passos
1. **Red**: escrever teste que falha (`pytest tests/... -x`)
2. **Green**: implementar código mínimo para passar
3. **Refactor**: limpar sem quebrar testes
4. Repetir para cada comportamento novo

Regras: nunca commitar com testes falhando; coverage ≥ 85% em módulos críticos.
