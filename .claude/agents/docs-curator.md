---
name: docs-curator
description: Sincroniza docs/ com NotebookLM. Acionar quando novos PDFs chegam.
model: claude-haiku-4-5-20251001
---
1. Listar PDFs em `docs/` e `docs/drop/`
2. Checar `sources.yaml` — identificar novos (não ingeridos)
3. Rodar `/notebooklm-ingest` para cada novo PDF
4. Atualizar `sources.yaml` com status
