# Plan: Pipeline Recipe UI

**Depends on:** `plan-randomness.md` (explicit RNG threading) — the random
signature fix must land first so that strategy order is stable and reproducible
when the user reorders steps.

## Current State

The pipeline is a draggable ordered list of phase toggles. Drag-to-reorder
already works. Two problems remain:

1. **No duplication** — each phase can only appear once, but running the same
   phase multiple times (e.g. two `NumberObscurer` passes) is a legitimate and
   useful pattern the backend already supports.
2. **Clutter when phases are off** — disabled phase cards still occupy space in
   the list. With several phases toggled off the panel becomes long and hard to
   scan.

## Approach

### Active-only recipe list + add panel

Show only *active* (enabled) phases as cards in the recipe list. Disabled
phases are removed from the list entirely.

To add a phase (or a second copy of one), the user opens an "Add step" control
— a compact dropdown or popover listing available phase types. Selecting one
appends a new card at the bottom of the list (above the pinned Renamer).

This makes the recipe list a true "what will run" view: short when simple, long
only when the user intentionally adds steps.

### Duplication

Each active card gets a duplicate (copy) button alongside the existing remove
button. Duplicating a card inserts an identical copy immediately below it,
including its strategy selection and parameters.

### Renamer constraint

The Renamer card is pinned to the bottom and cannot be dragged, duplicated, or
removed. A tooltip explains why it is locked.

### Custom strategy per card

Each card owns its strategy picker inline (already the case), including the
custom code editor in a collapsible section. Multiple instances of the same
phase type can have different strategies.

### Serialisation

The ordered recipe maps directly to the existing `ObfuscationConfig` fields.
Multiple instances of the same phase type require either:
- Sending a `phase_order: list[{type, config}]` field to `ObfuscationConfig`,
  with `pipeline.py` iterating it; or
- Keeping the current per-phase config but adding a `passes` count per phase.

The explicit ordered list is the cleaner approach and avoids ambiguity with
duplicate phases having different strategies.

## Files Affected

- Frontend: recipe list component (remove toggle-based disabled cards, add "Add
  step" control, add duplicate button per card)
- `app.py` / `ObfuscationConfig` — add `phase_order: list[PhaseConfig]` field
- `pipeline.py` — iterate `phase_order` instead of the fixed phase sequence

## Branch

`plan/pipeline-recipe`
