# QLearn Home — Design QA

## Target and evidence

- Source visual truth: `/var/folders/d6/fc320p510bg70wfkrtl215vr0000gn/T/codex-clipboard-2669b055-9943-4c5b-a53e-0f6d9e86445a.png`
- Source pixels: 1808 × 1376.
- Implementation screenshot: `.planning/qa/home-light-final.png`.
- Tall-viewport screenshot: `.planning/qa/home-light-tall-final.png`.
- Full-view comparison: `.planning/qa/home-light-comparison.png`.
- CSS viewports: 1280 × 720 and 1280 × 900; implementation pixels match CSS pixels at 1× density.
- Normalization: source and 1280 × 720 implementation were proportionally fitted onto equal 960 × 720 canvases, then placed side by side without stretching.
- State: `/home`, empty conversation, default light theme.
- Focused comparison: not needed; the reported defect concerns full-page vertical distribution, and the full-view captures keep the Hero/composer boundaries clearly readable.

## Findings

- No actionable P0/P1/P2 findings remain.
- The retained QLearn sidebar and functional composer intentionally make the implementation denser than the marketing-only reference.

## Fidelity surfaces

| Surface | Result | Evidence |
| --- | --- | --- |
| Fonts and typography | Pass | Display heading weight, compact UI labels, wrapping, line height, and hierarchy remain consistent at both tested heights. |
| Spacing and layout rhythm | Pass | The Hero expands into available height and the composer remains at the bottom with only its intended 18px page padding; there is no post-composer empty region, overlap, clipping, or horizontal overflow. |
| Colors and tokens | Pass | Light neutral surfaces and QLearn accent colors continue through the existing theme tokens. |
| Image quality | Pass | The locally served source robot MP4 and poster remain sharp, correctly contained, and free of masking artifacts. |
| Copy and content | Pass | Branding, four learning starters, three companion actions, and existing composer controls remain present and readable. |

## Comparison history

1. P1 — the upstream empty-state grow spacer placed the composer inside the Hero and clipped content. Fixed by removing the spacer growth.
2. P2 — lower starter cards touched the composer at laptop height. Fixed with a balanced 6/6 grid and a 460px desktop minimum.
3. P2 — a fixed 460px Hero left increasing blank space below the composer on tall displays. Fixed by making `WelcomeCanvas` the flexible child that consumes all available pre-composer height.
4. Post-fix evidence — at both 1280 × 720 and 1280 × 900, the composer ends at the viewport's bottom padding and the Hero absorbs extra height. No further P0/P1/P2 differences were found.

## Primary interactions and runtime checks

- **Explain a concept** prefills the existing composer with its intended prompt.
- **Solve a hard problem** prefills the intended prompt and switches the capability selector to Solve.
- Companion links retain the existing chat-history, knowledge, and notebook routes.
- Local robot video returns HTTP 200 as `video/mp4` and renders in-browser.
- Browser console errors: none.
- Frontend API proxy `/api/v1/settings`: HTTP 200.
- Unified WebSocket through the frontend proxy: opens successfully.

final result: passed
