---
name: research
description: Consulta bibliográfica via NotebookLM. Requer notebook_id preenchido em .claude/docs/sources.yaml.
---
## Guard de inicialização

Verificar `.claude/docs/sources.yaml` antes de executar:
- Se `notebook_id: ""` → NotebookLM não inicializado.
- Instruções: acesse notebooklm.google.com, crie notebook, preencha notebook_id, rode /notebooklm-ingest.

Até inicialização: este comando retorna erro de guard.
