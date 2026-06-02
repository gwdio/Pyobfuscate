# Plan 3: Collatz Engine — O(n) Fix

## The Problem

`get_loop_index_setup()` emits a call to `resolve_collatz` at the top of every loop body iteration. `resolve_collatz` walks from `self.target` (the fixed starting value) forward through the Collatz sequence until it reaches the current value of `num_var`. On the k-th iteration `num_var` is k steps away from `self.target`, so `resolve_collatz` takes O(k) steps. Summed over n iterations: O(1 + 2 + ... + n) = **O(n²)**.

## The Fix

The Collatz state machine in `num_var` already handles the loop condition (`num != seed`) and the advance step (halve or `a*num+b`). The only reason `resolve_collatz` exists is to derive the actual loop index value from `num_var`'s current position in the sequence. That derivation is what's expensive.

Replace it with a plain counter:

- Add a new variable (e.g. `idx_var`) initialized to `self.start` before the while loop.
- In `get_loop_index_setup`, assign `loop_var = idx_var` instead of calling `resolve_collatz`.
- In `get_advance`, append `idx_var += self.step` after the Collatz step on `num_var`.
- Remove `resolve_collatz` injection entirely.

The Collatz sequence still drives the loop condition and termination — it remains the obfuscated control structure. The index derivation becomes O(1) per iteration → **O(n) total**.

## What Changes

| | Before | After |
|---|---|---|
| `loop_var` source | `resolve_collatz(...)` call | `idx_var` (plain counter) |
| `resolve_collatz` helper | Injected into module | Removed |
| Loop condition/advance | Collatz `num_var` | Collatz `num_var` (unchanged) |
| Complexity | O(n²) | O(n) |

## Files Affected
- `LoopObfuscation/obfuscation_strategies.py` — `CollatzStrategy` only
  - `__init__`: add `self.idx_var = naming.get_name('idx')`
  - `get_initial`: add assignment `idx_var = self.start`
  - `get_loop_index_setup`: replace `resolve_collatz` call with `loop_var = idx_var`
  - `get_advance`: append `idx_var += self.step`
  - `inject_functions`: remove entirely (or return tree unchanged)
