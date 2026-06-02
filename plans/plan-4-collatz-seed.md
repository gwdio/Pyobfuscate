# Plan 4: Collatz Seed Determination — Hybrid Approach

## Problem with Current Backstepping

`_collatz_forward` doesn't discover a sequence — it generates one semi-randomly and records the endpoint. The 95% triple-step rate helps, but there's no guarantee any particular sequence shape is produced, and short loops can still end up uninteresting by chance.

---

## Proposed Approach

Sequences are represented as a binary list where `1 = x3+1` and `0 = /2`.

For all loops, the sequence begins with a brute-forced prefix:
1. Generate a random binary sequence of some prefix length (e.g. min(n, 10) steps).
2. Brute-force a `seed` that satisfies it — for each candidate, simulate the prefix forward: `1` requires the current value to be odd, `0` requires it to be even. Reject and retry if any step's parity constraint fails. With short prefixes this is fast.
3. For short loops (n < 10): the whole sequence is the brute-forced prefix, done.
4. For long loops (n ≥ 10): run the existing `_collatz_forward` backstepping for the remaining `n - prefix_length` steps starting from wherever the prefix left off. The prefix guarantees an interesting opening; the tail is left to chance.

---

## Files Affected

- `LoopObfuscation/obfuscation_strategies.py` — `CollatzStrategy.__init__` and `_collatz_forward`
  - Add `_random_sequence(length)`: returns a random binary list of 0s and 1s
  - Add `_brute_force_seed(sequence)`: iterates candidate seeds until one satisfies all parity constraints for the given sequence; returns `(seed, target)` pair
  - Update `__init__`: always generate a brute-forced prefix first; for long loops, continue with `_collatz_forward` from the prefix endpoint for the remaining steps
  - `target` and `seed` assignment logic stays the same; only how they're found changes
