---
status: resolved
trigger: "一大堆错误，各种500报错。用goal修复，直到没有错误。另外标题不能直接全学这两个字，改为我起好的名字。"
created: 2026-08-03
updated: 2026-08-03
---

# QLearn preview 500 errors and branding

## Symptoms

- Expected: `http://localhost:3000/home` loads the complete QLearn application without 500 responses.
- Actual: the browser reports many errors and multiple HTTP 500 responses.
- Error messages: HTTP 500 responses; exact endpoints to be established from container and proxy logs.
- Timeline: observed after launching the isolated frontend-only Docker preview.
- Reproduction: open `http://localhost:3000/home` and allow the page to load its API-backed state.
- Branding: visible title must use the user-approved full name `全学 · 智能学习空间`, never the standalone `全学` lockup.

## Current Focus

- hypothesis: Confirmed and fixed.
- test: Completed full frontend, HTTP proxy, WebSocket, and container-log regression.
- expecting: No reproducible 500 responses or proxy connection failures.
- next_action: None.
- reasoning_checkpoint: Preserve the upstream relative-path proxy contract; correct the isolated Docker topology instead of modifying `web/lib/api.ts`, `web/proxy.ts`, or backend routes.
- tdd_checkpoint: Existing Node suite (366 tests), locale parity, lint, TypeScript, and production build all pass.

## Evidence

- `qlearn-ui-preview` logs before the fix repeatedly showed `Failed to proxy http://localhost:8001/... ECONNREFUSED 127.0.0.1:8001`.
- The frontend-only container treated `localhost:8001` as its own loopback, where no backend process existed.
- A separate `qlearn-backend` container now exposes the healthy DeepTutor service on host port 8001, with runtime data isolated in Docker volume `qlearn-preview-data`.
- `qlearn-ui-preview` now receives `DEEPTUTOR_API_BASE_URL=http://host.docker.internal:8001`, while browser requests continue to use the original relative `/api/*` and `/api/v1/ws` paths.
- Final HTTP checks returned 200 for `/home`, `/space`, `/knowledge`, `/settings`, `/login`, `/api/v1/settings`, `/api/v1/settings/llm-options`, `/api/v1/tools`, `/api/v1/knowledge/list`, and `/api/v1/subagents/settings`.
- Final WebSocket handshake through `ws://localhost:3000/api/v1/ws` opened successfully.
- Frontend and backend logs contained no 500, proxy, connection-refused, traceback, or runtime error entries after the fix.
- Rendered HTML contains `<title>全学 · 智能学习空间</title>` and the credits `Songkun Ji`, `北京信息科技大学`, and `北京全学教育`.

## Eliminated

- Frontend build/type failure: production build completed all 57 routes.
- Locale key mismatch: i18n parity check passed.
- API contract regression: no transport boundary files or backend API schemas were changed.
- Backend unavailability after correction: root endpoint and representative APIs remained healthy.

## Resolution

- root_cause: The local preview ran Next.js alone in Docker. Its proxy target defaulted to `localhost:8001`, which pointed inside the frontend container instead of to a DeepTutor backend, so API proxy attempts failed with `ECONNREFUSED` and surfaced as HTTP 500 responses.
- fix: Run the backend in its own healthy Docker container, persist only its runtime data in a named Docker volume, and point the frontend container's server-side proxy to `host.docker.internal:8001`. Keep browser API and WebSocket paths relative and unchanged. Complete the QLearn branding layer with the full Chinese name, QLearn English name, Lucide icon set, clean Chinese sans stack, and replacement credits.
- verification: `npm run i18n:check` passed; lint completed with 0 errors; 366/366 Node tests passed; Next.js production build and TypeScript checks passed for 57 routes; representative pages and APIs returned 200; proxied WebSocket opened; final logs were clean.
- files_changed: `web/app/layout.tsx`, `web/tailwind.config.js`, `web/components/common/BrandLockup.tsx`, `web/components/layout/AppShell.tsx`, `web/components/sidebar/SidebarShell.tsx`, `web/components/qlearn/WelcomeCanvas.tsx`, `web/components/settings/SubagentSettingsEditor.tsx`, `web/locales/zh/app.json`, plus the broader QLearn presentation files already in this worktree. No backend or transport boundary source file was changed.
