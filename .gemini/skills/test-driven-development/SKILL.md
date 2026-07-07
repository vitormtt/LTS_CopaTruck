---
name: test-driven-development
description: Aplica ciclo red-green-refactor para features novas ou correções com comportamento observável. Escreve teste que falha PRIMEIRO, implementa o mínimo para passar, refatora mantendo verde. Ativa em "implementar <feature>", "fix <bug>" com comportamento externo, ou pedido explícito por TDD.
---

# test-driven-development

Ciclo disciplinado para features e bugs com comportamento observável. **Não pular etapas.**

## Quando acionar

- Nova feature com API externa (função pública, endpoint, CLI, UI).
- Bug report com reprodução clara — reproduz como teste ANTES de corrigir.
- Refactor de módulo crítico — cobrir comportamento atual com testes antes de mexer.

**Não acionar** quando:
- Mudança puramente estrutural (mover arquivo, renomear privado).
- Experimento descartável / spike.
- Ajuste de config sem lógica.

## Ciclo

### 🔴 Red — teste que falha

1. Identificar **1 comportamento observável** (não múltiplos).
2. Escrever teste com:
   - Nome descritivo: `test_<funcao>_<condicao>_<resultado_esperado>`.
   - Arrange — dados de entrada explícitos.
   - Act — chamada única do SUT (system under test).
   - Assert — verificação focada (1–3 asserts max).
3. Rodar → **confirmar que falha pelo motivo certo** (não por import error, sintaxe, etc.).
   - Se falhar por infra, corrigir e reiterar até falhar pelo motivo esperado.

### 🟢 Green — mínimo para passar

1. Implementar o **menor código possível** que faz o teste passar.
2. Evitar over-engineering; é OK fake/hardcode inicial se só há 1 caso.
3. Rodar o teste novo + suite completa do módulo → verde em ambos.

### 🔵 Refactor — mantendo verde

1. Remover duplicação introduzida.
2. Nomear melhor se aparecer pattern.
3. Extrair helpers quando houver 3+ usos idênticos (não antes).
4. Rodar testes a cada pequena mudança — nunca refactor sem rodar.

## Repetir

Voltar ao Red com o **próximo comportamento**:
- edge case (vazio, negativo, overflow, unicode, limite do tipo);
- ramo alternativo (erro esperado);
- interação entre componentes.

## Regras

- **Um teste por commit** (ou um grupo coerente), para bisect fácil.
- **Nunca** escrever 5 testes e então implementar.
- **Nunca** pular Red — teste que nunca falhou pode estar verde por acidente.
- Coverage segue naturalmente; não é meta primária.
- Se um teste vira instável (flaky), pausar feature e investigar causa — tolerar flaky é como admitir bug aleatório.

## Anti-patterns

- Testar implementação ("o método X chama o método Y"). Teste comportamento.
- Muitos mocks — acopla ao design atual, quebra em refactor.
- Setup gigante em `beforeEach` — fixtures focadas são melhores.
- Assert genérico (`assert result is not None`) — ser específico.
- Ignorar teste quebrado (`@skip`, `it.skip`) sem issue aberta.

## Stacks

- **Python**: `pytest -k test_<nome> -x --tb=short` para ciclo rápido.
- **TypeScript**: `vitest run <file> --reporter=verbose`.
- **MATLAB**: `runtests('tests/unit/TestMyThing.m')`.

## Relatório final

Após ciclo TDD de uma feature, reportar:
- Comportamentos cobertos (lista de `test_*` nomes).
- Arquivos alterados.
- Próximos comportamentos possíveis não cobertos (backlog).
