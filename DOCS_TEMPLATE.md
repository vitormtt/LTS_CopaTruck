# DOCS_TEMPLATE.md — Manual Definitivo

> vitormtt/claude-code-template v0.2.0  
> Ecossistema Multi-Stack Ultra-Token-Efficient para Claude Code

---

## 1. Inicializar novo projeto

### 1.1 Clonar o template

```bash
# Opção A: GitHub CLI (recomendado)
gh repo create meu-projeto --template vitormtt/claude-code-template --private --clone
cd meu-projeto

# Opção B: Git manual
git clone https://github.com/vitormtt/claude-code-template.git meu-projeto
cd meu-projeto
git remote set-url origin https://github.com/SEU_USER/meu-projeto.git
```

### 1.2 Primeira sessão Claude Code

```bash
claude  # Inicia Claude Code na pasta do projeto
```

O hook `SessionStart.ps1` executa automaticamente e:
- Detecta a stack do projeto (Python / NestJS / MATLAB / Docker / misto)
- Injeta o `@import` correto no `CLAUDE.md` para a stack detectada
- Lê `AGENTS.md` para recuperar memória de sessões anteriores
- Exibe fingerprint do projeto

### 1.3 Configurar variáveis de ambiente

Copie e edite o `.env` local:

```bash
cp .env.example .env  # se existir
```

Variáveis relevantes para o template:

```env
CLAUDE_TOKEN_BUDGET=50000        # Limite de tokens por sessão (CostGuard)
CLAUDE_COST_GUARD_ENABLED=true   # Ativar/desativar monitor de custo
NOTEBOOKLM_HOME=.claude/.notebooklm
```

---

## 2. Pesquisa Zero-Token via NotebookLM

### Como funciona

PDFs técnicos vivem no **NotebookLM** — não são lidos diretamente pelo Claude, economizando tokens de input.

### Fluxo de adicionar fonte

```
1. Mova o PDF para docs/drop/
2. Execute /notebooklm-ingest no Claude Code
3. O agente docs-curator sincroniza com o NotebookLM
4. Atualiza .claude/docs/sources.yaml
```

### Estrutura do `sources.yaml`

```yaml
# .claude/docs/sources.yaml
sources:
  - id: tire-model-pacejka
    title: "Tire and Vehicle Dynamics — Pacejka"
    notebook: "vehicle-dynamics"
    tags: [tire, pacejka, magic-formula]
    added: 2026-04-27
  
  - id: nestjs-docs-v10
    title: "NestJS Official Documentation v10"
    notebook: "backend-stack"
    tags: [nestjs, typescript, api]
    added: 2026-04-27
```

### Consultar via Claude Code

```
/research Como o modelo de Pacejka calcula a força lateral do pneu?
/research Qual é a diferença entre Guards e Interceptors no NestJS?
```

O Claude Code consulta o NotebookLM sem baixar o PDF, retornando apenas o trecho relevante.

---

## 3. Subagentes por Stack

### Como ativar

Digite no Claude Code:

```
use agent <nome-do-agente>
```

Ou referencie diretamente no prompt:

```
@tdd-enforcer implemente a feature X
@security-guard revise este PR
@architect revise o design do módulo Y
```

### Tabela de agentes

| Agente | Modelo | Uso principal | Custo relativo |
|--------|--------|---------------|----------------|
| `tdd-enforcer` | Sonnet | Feature nova com TDD | 🟡 Médio |
| `security-guard` | Haiku | Audit pré-commit/PR | 🟢 Baixo |
| `architect` | Sonnet | Design review | 🟡 Médio |
| `low-cost-runner` | Haiku | Leitura/catalogação | 🟢 Baixo |
| `code-reviewer` | Sonnet | Code review completo | 🟡 Médio |
| `bug-hunter` | Sonnet | Root cause análise | 🟡 Médio |
| `docs-curator` | Haiku | Sync NotebookLM | 🟢 Baixo |

### Workflow TDD (comando rápido)

```
/tdd <descrição da feature>
```

Exemplos:
```
/tdd endpoint POST /vehicles com validação de VIN único
/tdd função de integração Runge-Kutta 4a ordem para modelo 9-DOF
/tdd serviço de autenticação JWT com refresh token
```

---

## 4. Lendo o AGENTS.md

O arquivo `AGENTS.md` na raiz é a **memória persistente** do projeto entre sessões.

### Seções e como interpretá-las

#### Stack Fingerprint
Versões das dependências detectadas na última sessão. Use para verificar se o ambiente mudou.

#### Project Memory
Decisões arquiteturais tomadas. **Não regrida** sem registrar motivo. Antes de mudar uma decisão, adicione uma linha:
```
| 2026-05-01 | REVISAO de [decisão anterior]: novo motivo |
```

#### Compound Learning
Padrões que o agente descobriu ao longo do projeto. Consulte antes de criar algo novo — pode já existir um padrão testado.

#### Session Log
Um log das últimas 10 sessões. Use para entender o que foi feito recentemente sem precisar ler `git log` completo.

### Atualizar manualmente

Você pode editar `AGENTS.md` diretamente para:
- Registrar uma decisão importante fora de uma sessão Claude
- Adicionar um padrão ao Compound Learning
- Corrigir um log de sessão incompleto

O hook `Stop.ps1` atualiza automaticamente ao final de cada sessão.

---

## 5. CostGuard — Monitor de Tokens

Ativo por padrão. Exibe barra de progresso antes de cada tool use:

```
[CostGuard] [########------------] 40% (~20000/50000 tokens | 12 calls)
```

Para ajustar o budget:
```bash
# Aumente no .env ou diretamente:
export CLAUDE_TOKEN_BUDGET=100000
```

Para desativar temporariamente:
```bash
export CLAUDE_COST_GUARD_ENABLED=false
```

---

## 6. Estrutura final do template

```
├── CLAUDE.md                    # Roteador minimalista (não editar diretamente)
├── AGENTS.md                    # Memória persistente inter-sessões
├── DOCS_TEMPLATE.md             # Este manual
├── tasks/
│   └── todo.md                  # Plano de tarefas ativo
└── .claude/
    ├── CLAUDE.md                # Workflow, skills, proibições
    ├── settings.json            # Whitelist, hooks, env vars
    ├── rules/
    │   ├── common.md            # Git, commits, segurança (sempre ativo)
    │   ├── python.md
    │   ├── nestjs.md            # ★ novo v0.2.0
    │   ├── matlab.md
    │   ├── docker.md            # ★ novo v0.2.0
    │   ├── typescript.md
    │   ├── frontend.md
    │   └── yaml.md
    ├── agents/
    │   ├── security-guard.md    # ★ novo v0.2.0 (Haiku)
    │   ├── architect.md         # ★ novo v0.2.0 (Sonnet)
    │   ├── tdd-enforcer.md      # ★ novo v0.2.0 (Sonnet)
    │   ├── low-cost-runner.md   # ★ novo v0.2.0 (Haiku)
    │   ├── code-reviewer.md
    │   ├── bug-hunter.md
    │   └── docs-curator.md
    ├── commands/
    │   └── tdd.md               # ★ novo v0.2.0
    ├── hooks/
    │   ├── SessionStart.ps1
    │   ├── UserPromptSubmit.ps1
    │   ├── PreToolUse-Bash.ps1
    │   ├── PreToolUse-CostGuard.ps1  # ★ novo v0.2.0
    │   └── Stop.ps1
    ├── docs/
    │   └── sources.yaml         # Manifest NotebookLM
    └── skills/
```
