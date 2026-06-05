# Obfuscator UI — Design Spec

## 1. Purpose & goals

A recipe-style obfuscator with a configurable pipeline. The same surface must serve two very different users without compromise:

1. **The drive-by user** — opens the site, pastes, copies the result, leaves. Zero configuration, zero extra clicks. Defaults are already correct.
2. **The power user** — builds, reorders, and tunes a multi-stage pipeline, including compound stages with nested options.

Design priorities, in order:

- Dead-simple by default; configuration is opt-in and never in the way.
- One responsive surface for desktop and mobile — not two separate UIs.
- Compact at rest; roomy when editing a complex stage.
- The output is the payload. It gets the most space and a one-tap copy.

## 2. Core concepts

| Term | Meaning |
|------|---------|
| **Recipe** | The ordered list of stages applied top-to-bottom to the input. |
| **Stage** | One operation in the recipe (e.g. `Base64`, `Reverse`). The atomic, draggable unit. |
| **Compound stage** | A stage that contains its own sub-options (e.g. `Junk injector` → functions, lambdas, math ops) plus a single intensity control. |
| **Preset** | A named, pre-built recipe (`Default`, `Heavy`, `Minimal`) selectable in one action. |
| **Mode** | `Client` / `Server`. Gates which operations are available and which run. |

A stage has four states it can be in independently: **enabled/disabled**, **collapsed/expanded** (compound only), present in the recipe at some **position**, and configured with a **payload of sub-options** (compound only).

## 3. Layout

### Desktop (two columns)

```
┌─────────────────────────────────────────────────────────┐
│  Obfuscator                          [ Client | Server ] │  ← top bar, mode toggle top-right
├──────────────────────────┬──────────────────────────────┤
│  Input                   │  Output            · N chars  │
│  ┌────────────────────┐  │  ┌────────────────────────┐  │
│  │ paste source…      │  │  │                        │  │
│  └────────────────────┘  │  │   (largest pane;       │  │
│                          │  │    fills column height;│  │
│  Recipe        [Preset▾] │  │    own scroll if long) │  │
│  ┌────────────────────┐  │  │                        │  │
│  │ ⋮⋮ Base64      ⊙⧉🗑 │  │  │            [ Copy ]    │  │
│  │ ⋮⋮ Junk inj.  ⊙⌄⧉🗑 │  │  │                        │  │
│  │ ⋮⋮ Reverse     ⊙⧉🗑 │  │  └────────────────────────┘  │
│  └────────────────────┘  │                              │
│  [ + Add stage ]         │                              │
└──────────────────────────┴──────────────────────────────┘
```

Left column: input on top, recipe (pipeline of stage cards) below it. Right column: output, stretched to match the left column's height. The output is intentionally the largest single element on screen.

### Mobile (single column, result-first)

Do not shrink the two desktop columns into a phone width. Reflow instead:

- **Default view** is the output, full-bleed, with input as a compact box above it and a one-tap copy. The recipe collapses to a slim bar showing the active stages as chips: `Base64 → Junk → Reverse`.
- **Editing** pulls the pipeline up in a **bottom sheet**. Collapsed, the sheet is a peek (drag handle + chip summary); dragged up, it becomes the same vertical card list as desktop. The output stays visible behind/above the sheet so the user keeps context.

This single move buys "compact at rest" and "roomy when configuring" without a mode switch.

## 4. The default (drive-by) flow

This path must require **no clicks beyond paste and copy**:

1. Page loads with a default recipe already applied (or one decoded from the URL — see §9).
2. User pastes into the input. The pipeline **auto-runs** (debounced ~150 ms).
3. Output appears. Copy button is always visible.
4. User taps **Copy**, leaves.

The recipe is visible as chips/cards but never demands interaction. A casual user can ignore the entire left column.

## 5. The pipeline editor

### Stage card anatomy

Collapsed, every card is one line:

```
⋮⋮  [icon]  Stage name              ⊙  ⌄  ⧉  🗑
            sub-summary (compound)
```

- `⋮⋮` — drag handle (the **only** drag affordance; see §10).
- `⊙` — enable/disable toggle. Disabled stages stay in the recipe at 50% opacity and are skipped at runtime. (Cheap experimentation; never forces a delete.)
- `⌄` — expand/collapse, **compound stages only**.
- `⧉` — duplicate (inserts a copy directly below, carrying its config).
- `🗑` — delete.

### Adding stages

`+ Add stage` opens a **searchable picker** (a list/menu), not a drag-from-palette. The picker is the universal add path — identical on desktop and mobile. Dragging is reserved for reordering only.

Ops unavailable in the current mode appear in the picker **disabled with a lock icon** and a `server` tag, so the user can't build a recipe that silently won't run.

### Reordering

Drag a card by its grip handle to a new position. A drop indicator shows the insertion point. Reorder is vertical only.

## 6. Compound stages

The governing rule: **cap visible nesting at one expand.** A compound stage expands inline (accordion) to reveal its sub-options; nothing nests a second level inside that.

Represent the inside of a compound stage as:

- **Sub-options as toggle-chips** — a wrapping row of tap-to-toggle chips. Compact, touch-friendly, reads as "pick any."
- **One stage-level intensity slider** (e.g. `Density`) instead of per-type counts. Collapses an entire layer of nesting into one control.
- **A per-stage preset segmented control** (`Light / Medium / Heavy / Custom`) at the top of the expanded card. Sets the chips and slider in one tap; flips to `Custom` automatically the moment the user hand-edits anything.
- **A collapsed summary line** under the stage name that reflects the live config, e.g. `functions, lambdas · density 40%`, so the stage can stay closed almost always.

### Escalation rule

If a single sub-option grows to need more than one inline control of its own (e.g. `Functions` needs both arg-count and naming-style), the stage has outgrown the accordion. Promote it: the card becomes a one-line chip in the pipeline, and tapping `Configure` opens a **dedicated surface** — a right-side drawer on desktop, a bottom sheet on mobile. Never open a second accordion inside the first.

## 7. Client / Server mode

A segmented toggle in the top-right. Mode affects two things:

- **Availability** — server-only ops are locked in the picker while in `Client`.
- **Execution** — a server-only stage already in the recipe is skipped while in `Client`, and shows an inline warning on its card (`skipped in client mode`) rather than disappearing. Switching to `Server` activates it.

## 8. Output panel

- Monospace, soft-wrapped, its own scroll when long. Largest pane on screen.
- Character count beside the label, updated live.
- Persistent **Copy** (one tap → "Copied" confirmation). On mobile, tap-to-select the whole field as a fallback.
- Optional secondary action: download as file.

## 9. State, presets & sharing

The full recipe is serializable and **encoded in the URL** (mode, ordered stages, every stage's config). Consequences:

- "Defaults already set" is just a default URL.
- A configured pipeline is shareable by link and reproduces exactly on open.
- Presets are named recipes that replace the whole pipeline in one selection.

Example serialized state:

```json
{
  "mode": "client",
  "recipe": [
    { "type": "base64", "on": true },
    { "type": "junk", "on": true,
      "cfg": { "functions": true, "lambdas": true, "math": false,
               "deadcode": true, "decoy": false, "density": 40 } },
    { "type": "reverse", "on": true }
  ]
}
```

## 10. Interaction details (implementation notes)

- **Drag-and-drop:** use a pointer-based library (dnd-kit or SortableJS). Do **not** use native HTML5 DnD — it is broken on touch. Reorder is triggered only by the grip handle so it never conflicts with scroll.
- **Auto-run:** debounce input and config changes (~150 ms). No "Run" button on the simple path; expensive ops may show a spinner.
- **One UI, reflowed:** the card list is identical across breakpoints. Only its container changes (left column on desktop, bottom sheet on mobile).
- **Numbers:** round all displayed values (density %, char count).

---

## 11. Examples

### Example A — default recipe (drive-by user)

Input:

```
const greet = name => "hi " + name;
```

Recipe: `Base64 → Junk injector (functions, lambdas, dead code; density 40%) → Reverse`. User pastes, reads the obfuscated output, taps Copy, leaves. No card was ever touched.

### Example B — compound stage, expanded

`Junk injector` card opened:

```
⋮⋮ 🐛 Junk injector                         ⊙ ⌃ ⧉ 🗑
   functions, lambdas +1 · density 40%
   ─────────────────────────────────────────────────
   Preset   [ Light ][ Medium ][ Heavy ][ Custom ]
   Inject   [✓ Functions][✓ Lambdas][ Math ops ]
            [✓ Dead code][ Decoy ]
   Density  ──────●────────────  40%
```

Toggling `Math ops` on flips the preset row to `Custom` and updates the summary line to `functions, lambdas +2 · density 40%`.

### Example C — power-user flow

1. Start from the `Heavy` preset (full junk stage + Base64 + ROT13 + Reverse + To hex).
2. Drag `Reverse` above `ROT13` by its grip.
3. Duplicate `Base64` to double-encode.
4. Disable `To hex` (toggle off) to compare output without deleting it.
5. Switch to `Server` to add and run a `VM pack` stage.
6. Share the resulting URL with a teammate; it reopens identically.

### Example D — mode gating

In `Client` mode, the picker shows:

```
□ Base64
□ ROT13
□ Reverse
□ To hex
□ Junk injector
🔒 VM pack            server
```

`VM pack` is locked. If a recipe already contains it, its card reads `skipped in client mode` and contributes nothing to the output until the user switches to `Server`.

### Example E — escalation to a drawer

If `Junk injector` later gains per-type parameters (arg-count, naming style per injected function), it stops expanding inline. The card collapses to a single line with a `Configure` action that opens a right-side drawer (desktop) / bottom sheet (mobile) containing the detailed controls — keeping the pipeline list scannable.