---
name: notebooklm-ingest
description: Migra PDFs de `docs/` para o NotebookLM do projeto, preenche `.claude/docs/sources.yaml` com metadata (title, source_id, sha256, tags), remove PDFs do git e adiciona ao `.gitignore`. Ativa em `/notebooklm-ingest`, "migrar PDFs", "subir docs para NotebookLM".
---

# notebooklm-ingest — Migração docs/ → NotebookLM

Pipeline para remover PDFs volumosos do git e transferi-los para o NotebookLM, mantendo um manifest versionado de referência.

## Quando acionar

- `/notebooklm-ingest` ou `/notebooklm-ingest <dir>` (default: `docs/`).
- Primeiro setup do repo via `claude-bootstrap migrate-docs`.
- Novos PDFs chegam em `docs/drop/` ou `docs/`.

## Pré-requisitos

- `notebooklm` CLI instalado e autenticado.
- `yq` disponível (`choco install yq` ou `winget install yq`).
- Repo é um git repo inicializado.

## Procedimento

### 1. Garantir notebook existe

Ler `.claude/docs/sources.yaml`:

```bash
nb_id=$(yq '.notebook_id' .claude/docs/sources.yaml)
```

Se vazio, criar:
```bash
repo_name=$(basename "$(git rev-parse --show-toplevel)")
nb_id=$(notebooklm create "$repo_name | research" --format json | jq -r '.notebook_id')
yq -i ".notebook_id = \"$nb_id\" | .name = \"$repo_name | research\" | .created_at = \"$(date -I)\"" .claude/docs/sources.yaml
```

### 2. Enumerar PDFs

```bash
mapfile -t pdfs < <(find "${1:-docs}" -type f \( -iname '*.pdf' \) -not -path '*/drop/*')
```

Se `docs/drop/` existe, incluir também mas loggar separadamente (drops são novas adições).

### 3. Para cada PDF

```bash
for pdf in "${pdfs[@]}"; do
    sha=$(sha256sum "$pdf" | cut -d' ' -f1)

    # Pular se já ingerido (sha match em sources.yaml)
    if yq -e ".sources[] | select(.sha256 == \"$sha\")" .claude/docs/sources.yaml > /dev/null; then
        echo "[skip] $pdf (já ingerido)"
        continue
    fi

    title=$(basename "$pdf" .pdf | tr '_' ' ')
    src_id=$(notebooklm upload --notebook "$nb_id" --file "$pdf" --format json | jq -r '.source_id')

    yq -i ".sources += [{
      \"title\": \"$title\",
      \"path_original\": \"$pdf\",
      \"notebook_source_id\": \"$src_id\",
      \"sha256\": \"$sha\",
      \"added_at\": \"$(date -I)\",
      \"tags\": [\"paper\"]
    }]" .claude/docs/sources.yaml

    # Mover para staging local (fora do git)
    mkdir -p .local/notebooklm-staging
    mv "$pdf" ".local/notebooklm-staging/$(basename "$pdf")"
done
```

### 4. Atualizar gitignore e remover do git

Se a pasta-alvo tinha PDFs versionados:
```bash
git rm --cached 'docs/**/*.pdf' 2>/dev/null || true
# garantir .gitignore já cobre (o template padrão cobre)
```

### 5. Commit automático? Não.

**Nunca** commit automático. Após ingestão, reportar resumo:

```
Ingestão concluída:
  - N PDFs processados (M novos, K duplicatas puladas)
  - manifest atualizado: .claude/docs/sources.yaml
  - staging: .local/notebooklm-staging/
  - PRÓXIMO: revisar `git status`, ajustar tags em sources.yaml, commitar.
```

Usuário decide quando commitar (requer instrução explícita — comportamento sensível).

## Edge cases

- **PDF > 200MB**: NotebookLM impõe limite. Avisar e pular.
- **Rede caiu no meio**: restaurar `sources.yaml` do `git stash` ou do último commit; nenhum PDF foi movido antes do upload bem-sucedido (o `mv` só roda após `src_id` retornado).
- **PDF corrompido**: `notebooklm upload` retorna erro; logar e continuar com os próximos.
- **Duplicata**: detectada por SHA256 — pula sem upload.

## Interação com o usuário

- Antes de rodar em massa, perguntar se quer `--dry-run` para ver o que seria feito.
- Ao fim, mostrar `yq '.sources[] | .title' .claude/docs/sources.yaml | wc -l` — total no notebook.
- Sugerir ao usuário revisar tags e agrupar por tema em `sources.yaml`.

## Proibições

- Não commitar `sources.yaml` automaticamente.
- Não deletar PDFs definitivamente — apenas mover para `.local/notebooklm-staging/`.
- Não rodar em diretório que não seja do repo corrente (`git rev-parse --show-toplevel` deve ser o cwd ou ancestral).
