---
name: research
description: Consulta bibliografica zero-token usando Google NotebookLM. Lê `.claude/docs/sources.yaml` para descobrir o notebook ID do projeto, roteia a pergunta ao NotebookLM e retorna resposta com citações das fontes. Ativa em `/research`, `pesquise`, `o que o paper X diz`, ou qualquer intenção de consulta à literatura técnica do repo.
---

# research — Zero-Token Research via NotebookLM

Use esta skill quando precisar responder qualquer pergunta que seria tradicionalmente respondida lendo PDFs no `docs/`. **Não leia os PDFs** — consulte o NotebookLM.

## Quando acionar

- Usuário digita `/research <pergunta>` ou `pesquise X`.
- Qualquer citação a um paper/livro que está em `.claude/docs/sources.yaml`.
- Comparação entre abordagens descritas em múltiplas fontes.
- Dúvidas do tipo "o que o Gadola 1996 propõe?", "qual modelo de pneu no paper X?".

**Não acionar** quando:
- A informação está no código do repo (use Grep/Read).
- A informação é sobre configuração do próprio ambiente (não literatura).

## Pré-requisitos

1. NotebookLM CLI instalado e autenticado (`notebooklm login`).
2. `.claude/docs/sources.yaml` existe e tem `notebook_id` populado.

Se qualquer pré-requisito faltar, instruir o usuário a rodar:
```bash
claude-bootstrap migrate-docs   # primeira vez
# ou
notebooklm login                 # se só auth expirou
```

## Procedimento

1. **Ler `notebook_id`**:
   ```bash
   nb_id=$(yq '.notebook_id' .claude/docs/sources.yaml)
   ```
   Se vazio ou `""`, orientar bootstrap antes.

2. **Executar consulta**:
   ```bash
   notebooklm chat --notebook "$nb_id" "<pergunta do usuário>"
   ```
   Usar exatamente a pergunta do usuário — não reformular. Se a pergunta for muito genérica, pedir esclarecimento ANTES de consultar (cada chamada tem custo latência).

3. **Retornar resposta** com:
   - Texto da resposta do NotebookLM.
   - Lista de fontes citadas (extraída da resposta ou de `sources.yaml`).
   - Nota: `Consulta feita via NotebookLM — PDFs não foram lidos pelo Claude.`

## Exemplo

```
Usuário: /research qual a diferença entre quasi-steady e transient lap time sim?

Ação:
  notebooklm chat -n nb_abc123 "qual a diferença entre quasi-steady e transient lap time sim?"

Resposta (síntese):
> Quasi-steady assume equilíbrio dinâmico em cada ponto da pista, ignorando
> transitórios de transferência de carga [Gadola 1996, §3]. Transient simula
> a EDO completa com estados de suspensão e pneu [Sharp 2001, §4]...
>
> Fontes consultadas:
> - gadola1996.pdf
> - lap time simulation - compareison ss, quasi and transient.pdf
>
> _Consulta feita via NotebookLM — PDFs não foram lidos pelo Claude._
```

## Boas práticas

- **Uma pergunta por chamada**. Perguntas compostas confundem o NotebookLM — quebrar em sub-perguntas se necessário.
- **Contexto temporal**: se a pergunta envolver uma época ("abordagens recentes"), filtrar por `added_at` ou `tags` em `sources.yaml`.
- **Precisão de citação**: quando o usuário pedir página/figura específica, passar `--cite-pages` flag (se suportado pela versão do CLI).
- **Fallback**: se `notebooklm chat` retornar erro ou resposta vazia, dizer claramente "NotebookLM não tem informação relevante nas fontes atuais" — NÃO inventar resposta a partir de conhecimento geral.

## Integração com outros skills

- Antes de `create-pr` em features baseadas em paper: `/research` valida que a implementação bate com a fonte.
- Durante `bug-hunter`: se o bug for em equação física, `/research` confirma expected behavior.
