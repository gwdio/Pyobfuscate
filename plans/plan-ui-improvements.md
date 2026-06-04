# Plan: UI Improvements

## Goals

Three independent but related improvements to the frontend UX.

---

## 1. Start in Client Mode by Default

**Current state:** The app boots in client mode and partially switches to server
mode as a fallback when the client (Pyodide) is still loading, making the first
interaction janky.

**Problem:** Pyodide takes a few seconds to initialise. The current logic doesn't
account for that startup window, so to switch to server mode you have to click the client mode button and then the server mode button

**Approach:**

- remove the attemp to switch off `client` while pyodide is still loading, adapt the console logs to load status updates
- Block the Run button (or show a spinner) until Pyodide reports ready.
- Only surface the server option as an explicit user choice (toggle/button),
  never as an automatic fallback — remove the silent switch-to-server behaviour.
- If Pyodide fails to load entirely (network/browser issue), show a clear error
  message rather than a silent mode switch.

**Files likely affected:** frontend JS/TS that manages mode state and the Pyodide
initialisation callback.

---

## 2. Functional Pipeline Sliders

**Current state:** The sliders in the pipeline configuration panel are not
draggable — they appear as sliders but don't respond to drag input correctly.

**Approach:**

- Audit the slider components for missing `input` / `change` event handlers or
  incorrect CSS `pointer-events` / `z-index` stacking that intercepts clicks.
- Ensure the slider value is bound two-way so dragging updates the displayed
  value and the underlying config.
- Test on both desktop and touch (see item 3).

**Files likely affected:** slider component(s) in the frontend, associated CSS.

---

## 3. Mobile Usability

**Current state:** The UI is not usable on mobile (layout breaks, touch targets
too small, no responsive behaviour).

**Approach:**

- Add responsive breakpoints so the pipeline panel and editor stack vertically
  on narrow screens.
- Ensure touch targets (buttons, sliders, toggles) meet minimum 44 × 44 px
  tap target size.
- Test the full golden path (paste code → configure → run → copy output) on a
  375 px viewport.
- Avoid a separate mobile build — CSS media queries and flex/grid reflow are
  sufficient.

**Files likely affected:** global CSS / Tailwind config, layout components.

---

## Dependencies

None. All three improvements are self-contained frontend changes.

## Branch

`plan/ui-improvements`
