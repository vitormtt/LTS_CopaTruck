# Rules — Frontend (React 19 / Next 15)

Padrões para UI moderna 2026 — foco em **performance real**, a11y e manutenibilidade.

## Stack default

- **Next.js 15+** com App Router (RSC-first).
- **React 19** (Actions, `use()`, `useOptimistic`).
- **Tailwind CSS v4** + **shadcn/ui** para design system.
- **TypeScript estrito** (ver [`typescript.md`](./typescript.md)).
- **Zod** para validação em boundaries (forms, API).
- **TanStack Query** apenas em client components com cache não-trivial; RSC cobre o resto.

## Arquitetura

- **Server Components por default**; `"use client"` só quando precisa estado/effects/browser APIs.
- **Server Actions** para mutations (formulários, writes). Sem API routes para 90% dos casos.
- **Data Access Layer** separada em `src/server/dal/` — nunca acessar ORM direto em componente.
- **Streaming + Suspense** para latência percebida: wrap seções lentas em `<Suspense fallback={<Skeleton/>}>`.
- **Parallel routes / intercepting routes** para modais e layouts compostos.

## Acessibilidade (WCAG 2.2 AA)

Inegociável. Todo componente deve ter:

- **Semântica HTML correta**: `<button>` para ações, `<a>` para navegação, `<input type>` apropriado.
- **Labels** em todos os inputs (via `<label htmlFor>` ou `aria-label`).
- **Foco visível**: `focus-visible:` Tailwind; nunca `outline: none` sem substituto.
- **Contraste**: 4.5:1 texto normal, 3:1 texto grande (≥18pt ou ≥14pt bold).
- **Navegação por teclado**: Tab, Shift+Tab, Enter, Esc, setas em menus/listas.
- **Leitor de tela**: testar com NVDA/VoiceOver em componentes críticos.
- **`prefers-reduced-motion`**: respeitar em animações.
- **Skip links** em layouts com nav extenso.

## Performance (Core Web Vitals)

Targets de produção:

| Métrica | Target (p75 mobile) |
|---|---|
| LCP  | ≤ 2.5s |
| INP  | ≤ 200ms |
| CLS  | ≤ 0.1 |
| FCP  | ≤ 1.8s |
| TTFB | ≤ 800ms |

Técnicas:

- **`next/image`** sempre; `priority` no LCP hero.
- **`next/font`** para fontes; `display: swap` implícito.
- **Dynamic imports** (`next/dynamic`) para componentes pesados não-above-the-fold.
- **Tree-shaking**: sem barrels gigantes; imports específicos (`import { X } from 'lib/x'`).
- **Bundle size**: monitorar via `@next/bundle-analyzer`; alvo < 200KB JS inicial comprimido.
- **Server-side cache**: `revalidate` + `unstable_cache` + tags; invalidação por `revalidateTag`.
- **CSS**: Tailwind JIT; purge automático; evitar CSS-in-JS runtime em hot path.

## UX patterns

- **Optimistic UI** com `useOptimistic` em ações rápidas (like, toggle).
- **Pending states** claros via `useActionState` / `useFormStatus`; nunca botão morto sem feedback.
- **Error boundaries** por rota (`error.tsx`) + granular por seção quando crítico.
- **Empty states** sempre com CTA (não deixar tela vazia sem explicação).
- **Skeletons > spinners** para conteúdo estrutural previsível; spinners só em ações pontuais.
- **Toasts** para confirmações não-críticas; **dialogs** para ações destrutivas.

## Formulários

- **React Hook Form** + **Zod resolver** OU **nativo Server Actions** + Zod (preferível em Next 15).
- Validação:
  1. HTML constraints (`required`, `type`, `pattern`) — primeira barreira.
  2. Cliente (zod) — feedback rápido.
  3. Servidor (zod em Server Action) — fonte da verdade.
- Mensagens de erro próximas ao campo; `aria-invalid` + `aria-describedby`.
- Disable submit durante pending; preservar estado em erro.

## Componentes

- Um componente, um arquivo: `ComponentName/index.tsx` + `ComponentName.test.tsx` + `stories.tsx` (se Storybook).
- Props tipadas com `type`; `children: React.ReactNode` explícito.
- `forwardRef` com `ElementRef` + `ComponentPropsWithoutRef` para composition primitives.
- **shadcn/ui** como base; customizar via `cn()` + Tailwind, não forkar a menos que necessário.
- Evitar `React.memo` sem profiling; React 19 compiler cobre maioria dos casos.

## Testes

- **Vitest** + **@testing-library/react** para unit/component.
- **Playwright** para E2E (smoke paths + fluxos críticos).
- **Axe-core** (`jest-axe` ou `@axe-core/playwright`) em todo teste de componente complexo.
- Testar comportamento observável, não implementação (queries por role, label, text).
- Snapshots apenas para JSON estrutural; nunca para DOM renderizado.

## SEO

- `metadata` API do Next (por rota).
- Open Graph + Twitter Card em toda página pública.
- `sitemap.ts` + `robots.ts`.
- Structured data (JSON-LD) onde aplicável (Article, Product, BreadcrumbList).
- URLs canônicos; redirecionamentos em `next.config.ts`, não via JS.

## Antipadrões proibidos

- `useEffect` para fetch (use RSC ou TanStack Query).
- `useState` para dados do servidor (use RSC + revalidação).
- `window.location` para navegação (use `next/link` + `useRouter`).
- `div` clicável sem role/keyboard handler.
- Bundlear ícones inteiros (use `lucide-react` individual imports ou sprite).
- Inline styles para valores dinâmicos que deveriam ser classes condicionais (use `cn()`).
