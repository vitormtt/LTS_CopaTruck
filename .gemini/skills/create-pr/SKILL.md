---
name: create-pr
description: Cria Pull Request com título em Conventional Commits, corpo em template SARU (summary + test plan + checklist), abertura via `gh pr create`. Ativa em "abrir PR", "criar pull request", "/create-pr".
---

# create-pr

Padroniza abertura de PR. Usa `gh` CLI; assume que `main`/`master` é base.

## Pré-requisitos

- `gh` CLI autenticado (`gh auth status`).
- Branch atual tem commits divergentes da base.
- Todas as validações passaram (`/quality-gate`).

## Procedimento

### 1. Inspecionar estado

Em paralelo (um `Bash` único ou múltiplos em um turn):
```bash
git status -s
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
gh repo view --json defaultBranchRef,nameWithOwner -q '{base: .defaultBranchRef.name, repo: .nameWithOwner}'
```

### 2. Garantir push

Se branch não tem upstream:
```bash
git push -u origin HEAD
```

### 3. Compor título

Conventional Commits em **inglês**:

```
<type>(<scope>): <imperative subject, lowercase, <=70 chars>
```

Types aceitos:
- `feat` — nova funcionalidade externa
- `fix` — correção de bug
- `refactor` — mudança interna sem alterar API
- `perf` — melhoria de performance
- `test` — cobertura/correção de teste
- `docs` — apenas docs
- `chore` — infra, tooling, deps
- `sim` — alterações específicas de simulação (convenção SARU)
- `build`, `ci`, `style` — conforme caso

Derivar do histórico de commits: se forem múltiplos commits coesos, escolher o tipo predominante.

### 4. Compor corpo

Template:

```markdown
## Summary

<2-4 bullets descrevendo o que mudou e por quê>

## Changes

- `path/to/file.py` — o que mudou
- `path/to/other.ts` — o que mudou

## Test plan

- [ ] `pytest tests/unit/test_<módulo>.py` — verde
- [ ] `/quality-gate` — passa
- [ ] Teste manual: <passo a passo se aplicável>

## Checklist

- [ ] Sem secrets commitados
- [ ] Conventional Commits respeitados
- [ ] Rules de stack aplicadas (ver `.claude/rules/`)
- [ ] Docs atualizados se API mudou
- [ ] `sources.yaml` atualizado se novos PDFs ingeridos

## Context

<link para issue, paper, conversa — opcional>
```

### 5. Executar

```bash
gh pr create \
  --base "$BASE" \
  --title "<titulo>" \
  --body "$(cat <<'EOF'
<corpo>
EOF
)" \
  --draft  # usar --draft se ainda não está pronto para review
```

### 6. Retornar URL

Ao concluir, imprimir:
- URL do PR.
- Reviewers sugeridos (baseado em `CODEOWNERS` se existe, ou colaboradores frequentes via `git log`).

## Drafts

Criar como `--draft` quando:
- CI ainda não rodou;
- Alguma seção do checklist não está pronta;
- O usuário quer feedback antes de merge.

## Atualizar PR existente (em vez de criar novo)

Se já existe PR aberto para a branch:
```bash
existing=$(gh pr view --json number -q .number 2>/dev/null || true)
if [ -n "$existing" ]; then
    gh pr edit "$existing" --body "<novo corpo>"
    echo "PR #$existing atualizado"
fi
```

## Proibições

- **Nunca** `gh pr create` com título genérico (`update code`, `changes`, `wip`).
- **Nunca** push direto em `main`/`master` — sempre via PR.
- **Nunca** merge automático (`--auto`) sem solicitação explícita.
- Não reabrir PRs fechados sem autorização.
- Se `gh auth status` falhar, parar e pedir `gh auth login`.

## Integração

- Antes: `/quality-gate` (bloqueia se falhar).
- Antes (opcional): `security-auditor` para PRs sensíveis.
- Depois: gravar URL do PR em issue relacionada se houver.
