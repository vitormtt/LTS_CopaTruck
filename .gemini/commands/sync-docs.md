---
description: Sincroniza docs/ e docs/drop/ com o NotebookLM do projeto
argument-hint: [--dry-run]
---

Invoque o sub-agent `docs-curator` para executar scan completo:

1. Lista todos os PDFs em `docs/` e `docs/drop/`.
2. Compara com `.claude/docs/sources.yaml` e com sources atuais no NotebookLM.
3. Ingere novos PDFs via skill `notebooklm-ingest`.
4. Sugere tags para fontes sem tags (além do default `paper`).
5. Reporta:
   - Fontes novas ingeridas.
   - Fontes fantasmas (no manifest, ausentes do NotebookLM).
   - Fontes órfãs (no NotebookLM, ausentes do manifest).
   - PDFs em `.local/notebooklm-staging/` aptos para limpeza (> 30 dias).

Se `$ARGUMENTS` contiver `--dry-run`, apenas mostrar plano **sem executar** uploads, moves ou delete.

**Importante**: nenhum commit ou delete automático. Todas as ações pendentes aguardam confirmação do usuário no final do relatório.
