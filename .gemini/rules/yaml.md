# Rules — YAML

Padrões para arquivos de configuração, CI/CD e manifests (GitHub Actions, docker-compose, pyproject-like, sources.yaml).

## Sintaxe & estilo

- **Indentação: 2 espaços**, nunca tabs.
- Strings sem aspas quando unambiguous; aspas duplas `"..."` quando contêm `:`, `#`, `%`, ou começam com número/hífen.
- Listas: **hífen + espaço** (`- item`), alinhadas com a chave pai.
- Linhas ≤ 100 caracteres; quebrar strings longas com `>`, `|`, ou `>-`/`|-` conforme preservação de newline desejada.
- Anchors (`&`) e aliases (`*`) OK para DRY em valores repetidos — mas não abusar (limite compreensão).
- Um documento YAML por arquivo, exceto quando o formato exige `---` multi-doc (Kubernetes).

## Lint

- **`yamllint`** como padrão. Config em `.yamllint.yml` na raiz:
  ```yaml
  extends: default
  rules:
    line-length: {max: 100}
    document-start: disable
    truthy: {allowed-values: ['true', 'false']}
  ```
- Em CI, falha em warnings.

## Schemas

- Usar **JSON Schema** para arquivos customizados (`.claude/docs/sources.yaml`, configs de projeto).
- Referenciar schema no topo quando suportado:
  ```yaml
  # yaml-language-server: $schema=https://.../sources.schema.json
  ```
- VSCode detecta `yaml-language-server` comment e ativa autocomplete + validação.

## GitHub Actions

- Workflows em `.github/workflows/*.yml`.
- Pinar actions por SHA ou tag major: `uses: actions/checkout@v4` (tag) ou `uses: actions/checkout@a12b345...` (SHA — mais seguro).
- `permissions:` mínimo necessário por job (princípio do menor privilégio).
- `timeout-minutes:` em todo job (evitar workflow travado consumindo minutos).
- `concurrency:` group para cancelar runs antigos do mesmo branch.
- Secrets via `${{ secrets.X }}`; nunca ecoar secrets em logs.
- Outputs entre jobs via `jobs.<id>.outputs` + `steps.*.outputs` — não parseaer logs.

## Docker Compose

- Versão atual: **sem** `version:` no topo (deprecated no Compose v2).
- `healthcheck` em serviços de dependência (DB, cache).
- `depends_on` com `condition: service_healthy` quando aplicável.
- Volumes nomeados > bind mounts para dados persistentes.
- `env_file: .env` para variáveis; nunca commitar `.env` com valores reais.

## Kubernetes / manifests

- `apiVersion` sempre o mais estável disponível.
- `resources.requests` + `resources.limits` obrigatórios em produção.
- `livenessProbe` + `readinessProbe` distintos.
- Labels padrão: `app.kubernetes.io/name`, `app.kubernetes.io/version`, `app.kubernetes.io/component`.

## Antipadrões proibidos

- Mistura de tabs e espaços.
- Booleanos como strings (`"true"`, `"yes"`, `"on"`) onde um bool é esperado.
- `null` implícito vs `~` vs string vazia — ser consistente por arquivo.
- Campos comentados como "opções futuras" — remover; versionamento está no git.
- Secrets em plaintext (usar Sealed Secrets, SOPS, ou gerenciador externo).
