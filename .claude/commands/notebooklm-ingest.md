---
name: notebooklm-ingest
description: Ingere PDFs de docs/ no NotebookLM. Requer notebook_id preenchido em .claude/docs/sources.yaml.
---
## Guard de inicialização

Verificar `.claude/docs/sources.yaml`:
- Se `notebook_id: ""` → inicializar conforme /research antes de executar.

## Passos (após inicialização)
1. Ler `sources.yaml` e listar PDFs com `status: pending_ingest`
2. Para cada PDF: fazer upload para o notebook
3. Atualizar status para `status: ingested`
