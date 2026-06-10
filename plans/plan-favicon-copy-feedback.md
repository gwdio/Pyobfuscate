# Plan: Favicon + Copy Button Feedback

Two small, independent frontend polish tasks.

---

## 1. Favicon

**Goal:** A `favicon.ico` that evokes the project's identity — a snake that has
tied itself into a knot, rendered as a simple arrow curling back on itself.

**Design:** Single-colour SVG (snake-green, ~`#4ade80`) on a transparent/dark
background. Shape: a thick curved arrow where the tail curls inward and overlaps
the head — like an ouroboros fragment or a looped arrow that has eaten its own
path. Keep it legible at 16 × 16 px (the primary favicon size).

**Approach:**

1. Draw the icon as a 32 × 32 SVG (`frontend/favicon.svg`) using a thick
   stroke-based arc + arrowhead. One `<path>` or `<polyline>` is enough — no
   fills other than the arrowhead triangle.
2. Export / embed as `frontend/favicon.ico` (a 16 × 16 + 32 × 32 multi-size
   ICO, or a plain `.ico` wrapping the 32 px PNG). For a static site this can
   be done by converting the SVG to PNG via an `<canvas>` trick or just serving
   the SVG directly as `image/svg+xml`.
3. Add to `frontend/index.html` `<head>`:
   ```html
   <link rel="icon" type="image/svg+xml" href="favicon.svg">
   <link rel="icon" type="image/x-icon" href="favicon.ico">
   ```
   Serving both gives maximum browser compatibility; the SVG link is preferred
   by modern browsers.

**Files affected:** `frontend/index.html`, new `frontend/favicon.svg`,
optionally new `frontend/favicon.ico`.

---

## 2. Copy Button "Copied" Feedback

**Current state:** `app.js:938–941` — clicking "Copy" silently writes to the
clipboard. The button label never changes, so the user gets no confirmation.

**Desired behaviour:** After a successful copy, the button label changes from
"Copy" to "Copied" for ~1.5 s, then reverts. The button should not be
re-clickable during that window (disable it or ignore extra clicks via a flag).

**Approach:**

```js
$('copy-btn').addEventListener('click', () => {
  const text = $('output').value;
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    const btn = $('copy-btn');
    btn.textContent = 'Copied';
    btn.disabled = true;
    setTimeout(() => {
      btn.textContent = 'Copy';
      btn.disabled = false;
    }, 1500);
  }).catch(() => {});
});
```

The button is already re-enabled by `state.stages` render logic when output is
cleared (`app.js:706`), so the timeout reset will not conflict with that path.

**Files affected:** `frontend/app.js` (replace the listener at line 938).

---

## Dependencies

None. Both tasks are fully self-contained and can be done in either order.

## Branch

`plan/favicon-copy-feedback`
