# Docker Rules

> Carregado automaticamente quando `Dockerfile` ou `docker-compose.yml` detectados.

## Multi-stage Build (obrigatório)

Todo Dockerfile deve usar multi-stage para minimizar imagem final.

```dockerfile
# Stage 1: build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Stage 2: runtime (imagem mínima)
FROM node:20-alpine AS runtime
WORKDIR /app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
USER appuser
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

**Regra:** imagem final NUNCA deve conter `devDependencies`, código-fonte, ou ferramentas de build.

## .dockerignore (obrigatório)

Sempre criar `.dockerignore` na raiz:

```
node_modules/
.git/
*.log
.env*
dist/
coverage/
docs/
*.md
.claude/
tasks/
```

## Docker Compose

- Healthchecks obrigatórios em todos os serviços que outros dependem.
- Usar `depends_on` com `condition: service_healthy`.
- Secrets via variáveis de ambiente — NUNCA hardcoded no compose.
- Redes explícitas: nunca usar a rede default do Docker.

```yaml
services:
  api:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}      # ← env var, nunca valor direto
    depends_on:
      db:
        condition: service_healthy
    networks:
      - backend
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:3000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - backend

networks:
  backend:
    driver: bridge
```

## Imagens Base

| Stack | Imagem base preferida |
|---|---|
| Node.js | `node:20-alpine` |
| Python | `python:3.12-slim` |
| MATLAB Runtime | `mathworks/matlab-runtime:r2024b` |
| Nginx | `nginx:1.27-alpine` |
| Postgres | `postgres:16-alpine` |

- Sempre fixar versão — nunca usar `latest`.
- Alpine quando possível; `slim` para Python.

## Segurança

- Nunca rodar como `root` na imagem final — sempre `USER nonroot`.
- Escaneamento de vulnerabilidades: rodar `docker scout` ou `trivy` antes de push.
- Variáveis sensíveis via Docker Secrets (produção) ou `.env` local (dev) — nunca no `Dockerfile`.
- `COPY` específico — nunca `COPY . .` na imagem final.

## Volumes e Persistência

- Named volumes para dados persistentes: `db_data:/var/lib/postgresql/data`.
- Bind mounts apenas em dev: `./src:/app/src`.
- Nunca bind mount a raiz do projeto em produção.

## Proibições Docker

- `FROM ubuntu` ou `FROM debian` sem justificativa — usar variantes slim/alpine.
- Múltiplos `RUN` que poderiam ser encadeados com `&&`.
- Secrets ou .env commitados na imagem.
- `docker run --privileged` sem documentação explícita do porquê.
- `docker system prune -af` em automação sem gate de confirmação.
