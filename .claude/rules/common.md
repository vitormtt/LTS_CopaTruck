# Rules — Common (todas as stacks)

Diretrizes universais. Valem para Python, TS, MATLAB e qualquer arquivo texto.

## Git & Commits

- **Conventional Commits** obrigatório. Tipos: `feat`, `fix`, `chore`, `refactor`, `docs`, `test`, `perf`, `build`, `ci`, `sim`, `style`.
- Formato: `<type>(<scope>): <descricao imperativa, minuscula, <=72 chars>`.
- Escopo = área do repo (`src`, `tests`, `docs`, `tire-model`, `pipeline`, etc.).
- Corpo em PT-BR OK; título em EN (consistência com histórico do git).
- Nunca usar `--no-verify`, `--no-gpg-sign`, `--force-with-lease` sem instrução explícita.
- `main` é protegida: só entra via PR aprovado e com CI verde.
- **Antes de push**: `git status` + `git diff --stat` para confirmar o que vai.

## Branches

- `feat/<topico>`, `fix/<topico>`, `chore/<topico>`, `exp/<experimento>`.
- Rebase interativo apenas em branches próprias não publicadas.
- PRs pequenos e focados (idealmente < 400 linhas alteradas).

## Segurança

- **Zero secrets no repo**: varrer `.env`, `*.credentials*`, tokens, chaves API. Use `.env.example`.
- Pre-commit: `gitleaks` ou equivalente (CI enforça).
- OWASP Top 10 em qualquer I/O externo: validação, escape, rate-limit, parameterized queries, CSP para frontend.
- Dependências: preferir versões fixas em `pyproject.toml`; auditoria mensal (`pip-audit`).
- Nunca logar PII, tokens, payloads completos.

## Revisão de código

Antes de aprovar ou mesclar, verificar:
- [ ] Testes cobrindo golden path + ao menos 1 edge case.
- [ ] Sem `TODO`/`FIXME` sem issue aberta.
- [ ] Sem comentários explicando o *óbvio*; só comentários de *porquê* não-triviais.
- [ ] Sem código morto, imports não usados, prints de debug.
- [ ] Nomes significativos; sem `tmp`, `data`, `obj`, `val` soltos.
- [ ] Complexidade ciclomática dentro do razoável (quebrar função > ~30 linhas com >3 ramos).

## Estilo geral

- **Sem abstração prematura**: 3 repetições válidas ≠ abstração. Espere o 3º caso com diferença real antes de extrair.
- **Composição > herança** sempre que possível.
- **SRP** (Single Responsibility Principle): uma classe/função, uma razão para mudar.
- **YAGNI** (You Aren't Gonna Need It): nada de flag de feature sem consumidor real.
- Terminologia técnica: ISO 5725 (accuracy/precision), SAE J670 (dinâmica veicular), IEEE 754 (numérico).

## Documentação

- Código é a documentação primária; comentários para **porquê**, não **o quê**.
- READMEs curtos com: objetivo, setup, comandos principais, estrutura, licença.
- ADRs (`docs/adr/NNNN-titulo.md`) para decisões arquiteturais irreversíveis.
- API pública sempre documentada (docstrings Python).

## CI/CD

- Pipeline mínimo: **lint → type-check → test → build**.
- Falha em qualquer etapa bloqueia merge.
- Cache de dependências por lockfile hash.
- Coverage report ≥ 80% para módulos críticos.

## Idioma

- Código, commits, nomes de branch, docstrings, API pública: **inglês**.
- Comunicação humana (PR description, comentários issue, README seção de contexto): **PT-BR** aceitável quando o público for apenas interno.
