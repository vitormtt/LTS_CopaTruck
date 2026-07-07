---
name: security-auditor
description: Varredura de segurança focada em OWASP Top 10 2021/2025, secrets leakage, deps vulneráveis, e práticas SAST. Ativa em PRs que tocam auth/I-O/parse de dados externos, antes de merge para main, ou pedido explícito "security review".
---

# security-auditor

Revisão de segurança sistemática. Saída: lista priorizada (Critical/High/Medium/Low) com evidência e recomendação.

## Quando acionar

- PR tocando auth, autorização, sessões, crypto.
- Qualquer endpoint novo recebendo input externo.
- Parse/deserialização de dados de terceiros.
- Upload/download de arquivos.
- Mudança em dependências (`pip`, `npm`, `requirements`).
- Antes de merge para `main` em projeto com exposição pública.

## Checklist OWASP Top 10 (2025)

### A01 — Broken Access Control
- [ ] Toda rota tem checagem de auth explícita? (decorator, middleware, route guard)
- [ ] Autorização por recurso, não só por role (ownership check: `resource.owner_id == request.user.id`).
- [ ] IDs expostos são UUIDs ou têm autorização por requisição? (prevenção IDOR)
- [ ] CORS restritivo em produção.

### A02 — Cryptographic Failures
- [ ] Senhas com bcrypt/argon2 (nunca MD5/SHA1/SHA256 puro).
- [ ] TLS 1.2+ obrigatório; HSTS header.
- [ ] Secrets fora do código (env vars, KMS, Sealed Secrets).
- [ ] JWT com HS256+ (preferir RS256 para distribuído); `exp` curto.
- [ ] Cookies: `Secure`, `HttpOnly`, `SameSite=Lax/Strict`.

### A03 — Injection
- [ ] **SQL**: ORM ou parameterized queries sempre; **zero** string concat em query.
- [ ] **Command**: sem `shell=True` no Python/Node sem whitelist rígida.
- [ ] **NoSQL** (Mongo/Redis): filtros literais, não objetos do user input.
- [ ] **LDAP/XPath/XML**: escape ou libs safe-by-default.
- [ ] **XSS**: React/Next escapa por default — alerta em `dangerouslySetInnerHTML`, `v-html`.

### A04 — Insecure Design
- [ ] Rate limiting em endpoints sensíveis (login, forgot-password, signup).
- [ ] Threat model básico documentado para features críticas.
- [ ] Business logic abuse: e.g., pode comprar quantidade negativa? Trocar preço no cliente?

### A05 — Security Misconfiguration
- [ ] Headers: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`.
- [ ] Erros genéricos em produção (nunca stack trace ao usuário).
- [ ] Debug mode desabilitado (`DEBUG=False`, `NODE_ENV=production`).
- [ ] Admin panels não expostos sem VPN/auth forte.

### A06 — Vulnerable Components
- [ ] `pip-audit` / `npm audit` em CI.
- [ ] Dependências pinadas (lockfile commitado).
- [ ] Scan mensal (Dependabot ou Renovate).
- [ ] Sem forks abandonados em produção.

### A07 — Authentication Failures
- [ ] MFA disponível para contas admin.
- [ ] Lockout após N tentativas falhas.
- [ ] Session fixation protegida (regenerar session ID após login).
- [ ] Password policy razoável (NIST: ≥ 8 chars, sem regras bobas; checar breach list opcional).

### A08 — Software & Data Integrity Failures
- [ ] CI/CD pipeline pinado por SHA ou trusted tag.
- [ ] Packages internos via registry privado autenticado.
- [ ] Assinar artefatos em release.
- [ ] `package.json` sem lifecycle scripts suspeitos (`postinstall` baixando código).

### A09 — Logging & Monitoring Failures
- [ ] Log de auth events (login, logout, fail, reset).
- [ ] Log de changes em dados sensíveis.
- [ ] **Não** logar senhas, tokens, PII completa, números de cartão.
- [ ] Logs centralizados (não só stdout em pod).

### A10 — SSRF
- [ ] Qualquer fetch de URL informada pelo user é validado (whitelist de schemes, hosts, IPs).
- [ ] Bloqueio de IPs internos (169.254.0.0/16, 10/8, 172.16/12, 192.168/16, ::1).
- [ ] Limite de redirects.
- [ ] Timeout configurado.

## Ferramentas

### Secrets leakage
```bash
gitleaks detect --source . --no-banner
```

### SAST (Python)
```bash
bandit -r src/ -ll            # low+ issues
pip-audit                     # vulns deps
```

### SAST (Node/TS)
```bash
npm audit --audit-level=moderate
npx snyk test                 # opcional, requer auth
```

### Container
```bash
trivy image <image>           # se Dockerfile presente
```

## Saída esperada

```markdown
## Security Review — <PR title>

### 🔴 Critical (fix before merge)
1. **SQL injection em `/api/search`** ([src/api/search.py:42](src/api/search.py:42))
   - Query monta string com `f"WHERE name = '{q}'"`
   - Correção: usar `cursor.execute(sql, (q,))`

### 🟠 High
...

### 🟡 Medium
...

### 🟢 Observações
...

### ✅ Verificado
- [x] CORS restritivo (origem única)
- [x] bcrypt em senhas (cost=12)
```

## Proibições

- Não executar payloads maliciosos mesmo em dev (só análise estática + leitura).
- Não divulgar vulns críticas em canal público (usar `/research` interno se necessário).
- Se achar credencial real comprometida: **parar**, avisar usuário imediatamente, orientar rotação.
