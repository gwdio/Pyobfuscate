# 2a: Frontend Shell

**Depends on:** 1b (needs `GET /strategies` from 1a to populate controls, but shell can be built as static stub first)

## What

Static frontend in `frontend/`. A single-page app with:
- Code editor pane (textarea or CodeMirror) for input source
- Result pane showing obfuscated output
- Module control panel: ordered list of stages with enable toggle, per-stage config (density, probability, strategy dropdown)
- Execution path toggle: **Client (Pyodide)** / **Server (Lambda)**
- Submit button (wired to a stub at this stage — just echoes input back)
- Copy-to-clipboard button on output

No framework required — plain HTML/CSS/JS is fine unless complexity warrants otherwise.

## Files

- New: `frontend/index.html`
- New: `frontend/app.js`
- New: `frontend/style.css`
- `app.py` — add `GET /` static file route serving `frontend/` (or serve separately via Vite/etc. — TBD)

## Verification

1. Open `frontend/index.html` directly in a browser — layout renders, no console errors
2. Type code in input pane, click submit — stub echoes it to output pane
3. Drag to reorder a stage — order updates in the UI state
4. Toggle a stage off — it becomes visually inactive
5. Switch execution path toggle — selection persists in JS state (not yet functional)
