# Rules — TypeScript / Node

Padrões TypeScript 5+ / Node 20+ com foco em **prevenção de bugs** via sistema de tipos estrito.

## TypeScript

- **`tsconfig` estrito**: `"strict": true`, `"noUncheckedIndexedAccess": true`, `"exactOptionalPropertyTypes": true`, `"noImplicitOverride": true`, `"noFallthroughCasesInSwitch": true`.
- **Zero `any`**: use `unknown` + narrowing, ou gere tipo via `zod.infer`/generator. `// @ts-expect-error` com comentário e data.
- **Zero `as` casts** fora de boundaries (parse JSON externo, `Element.querySelector`). Prefira type guards.
- **Zod** (ou `valibot`) em toda fronteira: env vars, HTTP request/response, filesystem I/O, localStorage.
- `const` sempre; `let` apenas em loops/reassignment real; nunca `var`.
- `readonly` em propriedades de interface/type a menos que mutação seja intencional.
- Prefira `type` sobre `interface`, exceto quando usar `declare module` / augmentation.
- Unions discriminadas > flags booleanas proliferando.

## Estilo & organização

- **ESLint**: `@typescript-eslint/recommended-strict-type-checked` + `eslint-plugin-unicorn` + `eslint-plugin-import`.
- **Prettier** com defaults; não brigar com lint formatting.
- Imports: absolutos via alias `@/*` (definido em `tsconfig.paths`).
- Ordem: built-ins → deps → alias → relativos; `import type` para type-only.
- Arquivos: `kebab-case.ts`; componentes React: `PascalCase.tsx`.
- Um export default por arquivo **apenas** em páginas Next/rotas; resto = named exports.

## Funções & OOP

- Arrow functions para callbacks; declarations (`function`) quando precisa de hoisting/nome.
- Máx 3 args; acima disso, objeto de parâmetros com destruct.
- Classes **só** quando há estado + comportamento real (evitar "class wrapper" para agrupar funções).
- Composição > herança; prefira funções puras + objetos imutáveis.
- `private` usando `#field` (ECMAScript) > `private` TS (runtime-enforced).

## Erros

- **Nunca** `throw new Error('string')` sem categoria. Use classes de erro (`class NotFoundError extends Error`) ou `neverthrow`/`ts-pattern` Result.
- `try/catch` com tipo: `catch (error: unknown)` + narrowing.
- Async: sempre `await` ou `.catch`; promises flutuantes são bug.
- Não engolir erro: logar ou re-throw.

## Estrutura padrão

```
src/
├── app/            # Next.js App Router / entrypoints
├── components/     # UI (Frontend)
├── features/       # verticais de domínio
├── lib/            # utilitários puros
├── server/         # server actions, route handlers, DAL
├── types/          # types globais (evitar; prefira colocal)
└── env.ts          # zod env vars
tests/              # vitest unit + integration
```

- **Feature-first** em apps médios/grandes: cada feature traz UI + lógica + tipos.
- **Server-only** em código não-client: use `import 'server-only'` no topo de DAL.

## Testes (vitest / jest)

- `vitest` preferido (ESM-native, rápido). Jest apenas legacy.
- `src/**/*.{test,spec}.ts` colocal com código, ou `tests/` espelhando.
- Cobrir: happy path + erro esperado + edge case numérico/vazio.
- Mock só em boundaries; nunca mockar função que se está testando.
- **Playwright** para E2E; `@testing-library/react` para componentes (não testar implementação).
- Coverage ≥ 80% em `server/`, `lib/`, `features/`.

## Frontend (se React/Next)

Ver [`frontend.md`](./frontend.md) para detalhes. Resumo:
- Next 15 App Router + RSC-first; `"use client"` só quando precisa estado/effects.
- Tailwind + shadcn/ui padrão.
- `zod` + Server Actions para forms.
- Suspense + streaming para latência percebida.

## Node/Backend

- ESM puro (`"type": "module"` em `package.json`).
- `fetch` global > `axios` em Node 20+.
- Validação de env: `zod` em `env.ts`, importado no bootstrap.
- Logging estruturado: `pino` ou `winston` com níveis; nunca `console.log` em produção.
- Variáveis de ambiente: `.env.example` versionado; `.env.local` no gitignore.

## Tooling default

```jsonc
// package.json (trechos)
{
  "type": "module",
  "scripts": {
    "lint": "eslint . --max-warnings=0",
    "type-check": "tsc --noEmit",
    "test": "vitest run --coverage",
    "build": "next build"
  },
  "engines": { "node": ">=20" }
}
```

## Antipadrões proibidos

- `any`, `// @ts-ignore`, `Object as` sem guard.
- Mutação de props/state direto (React) ou arrays in-place (`.push` em imutáveis).
- Async IIFEs no topo de módulo (preferir boot explícito).
- Circular imports; `index.ts` barrels > 20 exports.
- `enum` numérico (use `as const` unions ou `enum` string explícito).
