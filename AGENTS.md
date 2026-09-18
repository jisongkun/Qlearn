# Qlearn — DeepTutor-Compatible UI Fork

## Qlearn Product and Compatibility Contract

Qlearn is a UI-focused fork of `HKUDS/DeepTutor`. Its product goal is to make
large, opinionated improvements to branding, information architecture, visual
design, responsive behavior, accessibility, and frontend interaction quality
without changing DeepTutor's actual capabilities or breaking the ability to
merge future upstream releases.

The downstream change registry and upstream merge runbook live in
`FORK-MAINTENANCE.md`. **Every agent and contributor must read that file in
full before changing code, configuration, dependencies, deployment, or
performing an upstream synchronization.** This is a mandatory preflight, not
optional background reading.

For every Qlearn-specific change, update `FORK-MAINTENANCE.md` in the same
focused commit when behavior, build, deployment, backend, API, event,
persistence, or an existing downstream patch is introduced, changed,
superseded, upstreamed, or removed. Before an upstream merge, record the target
version/commit, current baseline, dirty-worktree protection plan, and affected
QL IDs. After the merge, update the new baseline, reconciliation result for
every affected QL ID, verification evidence, deployment result, and remaining
follow-ups. An upgrade is not complete and must not be reported or deployed as
complete while this registry is missing or stale.

GitHub Actions is disabled for `jisongkun/Qlearn`. Do not enable or dispatch
repository workflows for CI, release, image publishing, or deployment unless
the user explicitly reverses this policy. Upstream-owned workflow files remain
in the fork only to reduce upstream merge churn; their presence is not
authorization to run them. Enforce the registry contract through this file,
local review, and the required local/container checks.

Qlearn currently has only a development/test deployment on `aliyuntokyo` in
`/data/home/shinji/Developer/Qlearn-test`. Build and restart it locally with
`deploy/aliyuntokyo/docker-compose.yml`. There is no Qlearn production
deployment today. If production is later authorized, publish source from the
authoritative `*-test` checkout to `hw135` via SSH/rsync and run Docker Compose
there; do not introduce GitHub Actions deployment. A Git push never authorizes
or performs deployment.

This contract is mandatory for all agents and contributors unless the user
explicitly authorizes a functional or compatibility-breaking change.

### Repository relationships

- `origin` is `https://github.com/jisongkun/Qlearn.git`.
- `upstream` is `https://github.com/HKUDS/DeepTutor.git`.
- Keep upstream history intact. Do not squash, rebase, or rewrite shared
  upstream commits merely to make the fork history look cleaner.
- Put Qlearn-specific work in small, focused commits. Keep visual-system,
  layout, copy, transport, and backend changes separate so upstream conflicts
  remain reviewable.
- Do not rename, relocate, or mechanically reformat upstream-owned files unless
  the UI change requires it. Broad formatting churn makes future merges harder.

### Architecture boundary

The codebase is a monorepo with logically separate applications:

- `web/`: Next.js 16, React 19, TypeScript frontend. This is the primary Qlearn
  customization surface.
- `deeptutor/`: Python/FastAPI backend and agent runtime. Treat this as
  upstream-owned and unchanged for UI-only work.
- `deeptutor_cli/` and `deeptutor_web/`: packaging and entry-point layers.
  Treat these as upstream-owned unless build integration genuinely requires a
  minimal change.
- `web/lib/`, `web/hooks/`, and frontend contexts may contain behavior and
  transport logic even though they live under `web/`. Do not assume every
  frontend file is presentation-only.

The repository may package both applications in one Docker image; that does
not erase the frontend/backend contract.

### Safe UI customization surface

Prefer changes in these areas:

- `web/app/` for layouts, route presentation, loading states, and page shells.
- `web/components/` for visual components and composition.
- `web/features/` for presentation-oriented feature composition.
- `web/public/` for Qlearn-owned static assets.
- `web/locales/` for user-facing copy, while preserving every existing locale
  key and keeping locale parity checks passing.
- Tailwind configuration, design tokens, CSS, icons, and motion definitions.

New Qlearn-specific design primitives should be additive and centralized. Build
a reusable design-system layer rather than scattering one-off styles across
upstream components.

### Functional contracts that must remain compatible

UI-only work must preserve all externally observable behavior, including:

- HTTP API paths, methods, query parameters, request bodies, status handling,
  and response-field interpretation.
- WebSocket paths, connection lifecycle, message schemas, event ordering,
  cancellation, reconnection, and streaming behavior.
- File-upload field names, accepted file behavior, previews, and download URLs.
- Authentication cookies, login/register flows, redirects, and authorization
  handling.
- Settings persistence, knowledge-base operations, chat/session behavior,
  notebooks, books, learning progress, memory, partners, subagents, tools, and
  capabilities.
- Existing route URLs, deep links, browser navigation, and bookmarked pages,
  unless an explicit compatibility redirect is added and tested.
- Accessibility semantics and keyboard behavior; a redesign must not make them
  worse.
- `web/lib/api.ts`, `web/proxy.ts`, and `web/lib/unified-ws.ts` are transport
  boundaries. Preserve their semantics for UI-only changes.

Do not modify `deeptutor/api/`, capability implementations, runtime settings,
event schemas, or persistence formats to make a UI implementation easier.
Adapt the presentation layer to the existing contract instead.

### Upstream-friendly implementation rules

- Prefer wrappers, composition, new Qlearn components, and design tokens over
  invasive rewrites of transport-aware upstream components.
- When an upstream component mixes data behavior and presentation, first
  preserve or extract the behavior behind the same public props, then replace
  only the presentation. Do not silently change its behavioral contract.
- Keep component public props and exported symbols stable when practical.
- Avoid copying backend-derived enums, capability names, or event schemas into
  a second manually maintained source of truth.
- Do not hard-code backend URLs. Browser API and WebSocket calls must continue
  through the existing relative-path/proxy architecture.
- Do not commit secrets, local runtime data, generated knowledge bases, model
  credentials, build output, or dependency directories.
- When resolving an upstream merge conflict, first preserve upstream behavior,
  then reapply the Qlearn visual layer. Never choose the Qlearn side solely
  because it looks newer.

### Required workflow for UI changes

Before implementation:

1. Identify the routes and components being redesigned.
2. Trace their API, WebSocket, auth, persistence, and context dependencies.
3. Record which behavior is invariant and which presentation is changing.

During implementation:

1. Keep data fetching, mutations, and event handling behavior intact.
2. Keep Qlearn-specific presentation changes isolated and reusable.
3. Preserve loading, empty, error, reconnecting, disabled, permission, and
   partial-stream states—not only the happy path.

Before considering the work complete, run the relevant available checks:

```bash
cd web
npm run lint
npm run test:node
npm run i18n:check
npm run build
```

For affected critical flows, also run or extend the relevant Playwright tests.
If a command cannot run because dependencies or services are unavailable,
report that explicitly; do not claim compatibility was verified.

### Upstream synchronization procedure

Use a merge-based synchronization flow so the fork relationship remains
auditable:

```bash
git fetch upstream
git switch main
git merge upstream/main
# resolve conflicts by preserving upstream behavior and reapplying Qlearn UI
git push origin main
```

After every upstream merge, at minimum verify the frontend build, locale parity,
API proxy behavior, authentication gate, primary chat WebSocket flow, knowledge
base flow, and any routes touched by conflict resolution.

## DeepTutor Upstream Architecture

## Overview

DeepTutor is an **agent-native** intelligent learning companion organized
around a two-layer plugin model — single-shot **Tools** invoked by the
LLM, and multi-stage **Capabilities** that take over a turn — exposed
through three entry points: CLI, WebSocket API, and Python SDK.

## Architecture

```
Entry Points:  CLI (Typer)  |  WebSocket /ws  |  Python SDK
                    ↓                   ↓                   ↓
              ┌─────────────────────────────────────────────────┐
              │              ChatOrchestrator                    │
              │   routes UnifiedContext → selected Capability    │
              │   (defaults to `chat`)                           │
              └──────────┬──────────────┬───────────────────────┘
                         │              │
              ┌──────────▼──┐  ┌────────▼──────────┐
              │ ToolRegistry │  │ CapabilityRegistry │
              │  (Level 1)   │  │   (Level 2)        │
              └──────────────┘  └────────────────────┘
```

All capabilities emit on a shared `StreamBus`; the orchestrator fans
events out to consumers. Runtime settings live in
`data/user/settings/*.json` — project-root `.env` files are intentionally
ignored.

### Level 1 — Tools

Single-function tools the LLM picks on demand. Four user-toggleable tools
surface in `/settings/tools`:

| Tool           | Description                                   |
| -------------- | --------------------------------------------- |
| `brainstorm`   | Breadth-first idea exploration with rationale |
| `web_search`   | Web search with citations                     |
| `paper_search` | arXiv preprint search                         |
| `reason`       | Dedicated deep-reasoning LLM call             |

The rest are **context-gated**: the chat capability auto-mounts them from
`ToolMountFlags` (presence of a KB, attachments, sandbox availability, …), and
any of them can also be force-enabled via `--tool`. Auto-mounted set: `rag`,
`read_source`, `read_memory`, `write_memory`, `read_skill`, `load_tools`,
`exec` (sandboxed Python/C/C++ or shell execution),
`list_notebook`, `write_note`, `web_fetch`, `github`, `cron`,
`ask_user` (pauses the turn and resumes with the user's reply), plus the
mastery-path tools. `geogebra_analysis` is parked under
`COMING_SOON_TOOL_TYPES`.

### Level 2 — Capabilities

Multi-stage pipelines that own the turn:

| Capability       | Stages                                                |
| ---------------- | ----------------------------------------------------- |
| `chat`           | exploring → responding (single agentic loop, default) |
| `mastery_path`   | responding (Guided Learning — chat loop + mastery tools, gated per topic type) |
| `deep_solve`     | planning → reasoning → writing                        |
| `deep_question`  | ideation → generation                                 |
| `deep_research`  | rephrasing → decomposing → researching → reporting    |
| `visualize`      | analyzing → generating → reviewing (SVG / Chart.js / Mermaid / HTML; or routes to Manim sub-stages via `render_type`) |
| `math_animator`  | concept_analysis → concept_design → code_generation → code_retry → summary → render_output |

All capabilities converge on `emit_capability_result()` in
`deeptutor/capabilities/_shared.py` so every turn emits the same envelope
(response payload + `cost_summary` from `UsageTracker`). Status copy and
prompts are i18n'd via `capabilities/prompts/{en,zh}/<name>.yaml`.

## CLI Usage

```bash
# Install
pip install deeptutor      # Full app (CLI + Web/API + packaged Web assets)
pip install deeptutor-cli  # CLI-only

# Run any capability
deeptutor run chat "Explain Fourier transform"
deeptutor run deep_solve "Solve x^2=4" -t rag --kb my-kb
deeptutor run visualize "Animate sine wave" --config render_mode=manim_video

# Interactive REPL
deeptutor chat
# (inside the REPL: /regenerate or /retry re-runs the last user message)

# Partners (IM-connected companions)
deeptutor partner list

# Knowledge bases, memory, server
deeptutor kb list
deeptutor kb create my-kb --doc textbook.pdf
deeptutor memory show
deeptutor serve --port 8001       # API server only
deeptutor start                   # backend + frontend together
```

## Key Files

| Path                                       | Purpose                              |
| ------------------------------------------ | ------------------------------------ |
| `deeptutor/runtime/orchestrator.py`        | `ChatOrchestrator` — unified entry   |
| `deeptutor/runtime/launcher.py`            | Backend + frontend lifecycle / port discovery |
| `deeptutor/runtime/registry/`              | Tool + Capability registries         |
| `deeptutor/runtime/bootstrap/builtin_capabilities.py` | Built-in capability class paths |
| `deeptutor/services/config/runtime_settings.py` | JSON settings + process-env overrides |
| `deeptutor/core/stream.py`, `stream_bus.py` | StreamEvent protocol + async fan-out |
| `deeptutor/core/tool_protocol.py`          | `BaseTool` + `ToolDefinition`         |
| `deeptutor/core/capability_protocol.py`    | `BaseCapability` + `CapabilityManifest` |
| `deeptutor/core/context.py`                | `UnifiedContext` dataclass            |
| `deeptutor/tools/builtin/__init__.py`      | All built-in tool wrappers           |
| `deeptutor/capabilities/`                  | Built-in capability implementations  |
| `deeptutor/app.py`                         | `DeepTutorApp` — Python SDK facade    |
| `deeptutor_cli/main.py`                    | Typer CLI entry point                |
| `deeptutor/api/routers/unified_ws.py`      | Unified WebSocket endpoint           |

## Dependency Layers

Public install paths and source extras are defined in `pyproject.toml`.
Requirements files mirror the same dependency groups for Docker/CI installs.

```
pip install deeptutor      — Full app (CLI + Web/API + packaged Web assets)
pip install deeptutor-cli  — CLI-only (LLM + RAG + providers + document parsing)
pip install -e .           — Source install for development

Source extras (.[ extra ], defined in pyproject.toml):
.[cli]            — CLI-only dependency set
.[server]         — Web/API server dependencies
.[partners]       — Partner channel SDKs  (legacy alias: .[tutorbot])
.[matrix]         — Matrix channel for Partners (matrix-nio; needs libolm)
.[matrix-e2e]     — Matrix with end-to-end encryption (matrix-nio[e2e])
.[math-animator]  — Manim addon (powers `visualize` Manim renders + `deeptutor run math_animator`)
.[dev]            — Test / lint tooling
.[all]            — Everything above
```
