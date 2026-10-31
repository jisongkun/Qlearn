---
status: resolved
trigger: "怎么一点击菜单一开始非常慢"
created: 2026-08-04
updated: 2026-08-04
---

# Menu first navigation is slow

## Symptoms

- Expected: Sidebar navigation should respond immediately on first click.
- Actual: The first visit to a menu route takes seconds; subsequent visits are fast.
- Error messages: None.
- Timeline: Observed in the current isolated local Docker preview.
- Reproduction: Open `http://localhost:3000/home` and click a menu route that has not yet been visited since the frontend container started.

## Current Focus

- hypothesis: Confirmed. The preview uses `next dev`, so Turbopack compiles each route on first request; automatic Link prefetching is production-only.
- test: Compare cold and warm requests for an unvisited route and isolate Next.js, proxy, application, and API timings.
- expecting: Cold request spends most time in `next.js`; warm request and API proxy are fast.
- next_action: None. The local preview now serves a precompiled standalone production bundle.
- reasoning_checkpoint: This is development-preview behavior, not a menu animation, API, WebSocket, or backend regression.
- tdd_checkpoint: Production build completed TypeScript checks and generated all 57 routes.

## Evidence

- Container command is `npx next dev --hostname 0.0.0.0 --port 3000`.
- `/memory/graph` cold request took 1.777 s; the immediate warm request took 0.064 s.
- Server timing attributed 1.645 s of the cold request to Next.js compilation, versus 6 ms warm.
- `/api/v1/settings` through the frontend proxy took 0.026 s.
- Existing logs show `/book` first visit at 7.6 s (7.5 s in Next.js), then 191 ms and 100 ms; `/partners` first visit at 3.6 s, then 73 ms; `/agents` first visit at 2.2 s, then 265 ms and 26 ms.
- Next.js official documentation states automatic `<Link>` prefetching runs only in production.
- The replacement image was built from the existing Dockerfile's `frontend-builder` target and now starts `.next/standalone/server.js` with `NODE_ENV=production`.
- After switching, cold requests measured `/partners` 27 ms, `/agents` 14 ms, `/book` 13 ms, `/space` 9 ms, `/memory` 10 ms, `/knowledge` 10 ms, and `/settings` 12 ms.

## Eliminated

- Backend/API latency: representative proxied API response was 26 ms.
- Proxy overhead: logged proxy time is typically single-digit to low tens of milliseconds.
- Menu transition animation: the delay occurs before an uncompiled route response and disappears after compilation.
- Persistent route rendering regression: warm navigation is fast.

## Resolution

- root_cause: The local Docker preview is a development server. Next.js/Turbopack compiles route bundles lazily on first access, and production automatic prefetching is disabled in development. Docker Desktop filesystem and container overhead can amplify that cold compile.
- fix: After user approval, build the frontend's optimized production image in Docker, replace the `next dev` preview container, and serve the precompiled standalone output with `node .next/standalone/server.js`. Preserve the existing backend proxy target and Docker isolation.
- verification: Production build and TypeScript checks passed for all 57 routes. After a fresh container start, representative first-route responses fell to 9–27 ms, the backend API remained about 34 ms, and the standalone server reported ready without development compilation.
- files_changed: Diagnostic record only; application source unchanged.
