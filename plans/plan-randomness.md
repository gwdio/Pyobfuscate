# Plan: Explicit RNG Threading

Replace all implicit `import random` / global-state calls with an explicit
`random.Random` instance threaded through every interface that needs randomness.

**Why:** The global `random` module is shared mutable state. Any call made
outside the `seeded()` context window — or from a different thread — can shift
the sequence. An explicit `rng` instance is owned by one pipeline run, makes
seeding trivially correct, and makes each method's randomness dependency
visible in its signature.

---

## Affected files

| File | What uses `random` today |
|------|--------------------------|
| `pipeline.py` | `seeded()` context manager — replaced by `rng` construction |
| `Injectors/inject_junk.py` | `random.randint`, `random.random` in `__init__` / `_inject_in_body` |
| `Injectors/junk_strategies.py` | `random.*` in every strategy's `get_junk()` and `__init__` |
| `Injectors/junk_conditional_strategies.py` | `random.*` in `get_junk()` |
| `Injectors/identity_strategies.py` | `random.choice` in `MixedIdentityStrategy.wrap()` |
| `Injectors/identity_injector.py` | `random.random` in `visit_*` |
| `Injectors/conditional_injector.py` | `random.random`, `random.choice` in `_inject_in_body` |
| `LoopObfuscation/obfuscation_strategies.py` | `random.*` in `CollatzStrategy.__init__` and `get_loop_index_setup` |
| `Encryption/number_obscure_strategies.py` | `random.getrandbits` in `FeistelNumberStrategy.__init__` and `XorStringNumberStrategy.obfuscate` |
| `Renaming/renamer.py` | `random.choice`, `random.choices` in `_generate_name` |

`Utils/random_seeder.py` is deleted entirely once `pipeline.py` no longer needs it.

---

## Interface changes

### Strategy method signatures

Every method that currently calls `random.*` gains an `rng: random.Random`
parameter. No other changes to the method's logic.

```python
# Before
class JunkInjectionStrategy:
    def get_junk(self) -> List[ast.stmt]: ...

# After
class JunkInjectionStrategy:
    def get_junk(self, rng: random.Random) -> List[ast.stmt]: ...
```

Same pattern for:
- `JunkConditionalStrategy.get_junk(self, rng)`
- `IdentityFuncStrategy.wrap(self, expr, rng)`
- `NumberObscureStrategy.obfuscate(self, value, rng)`

### Strategy constructors that use random

`CollatzStrategy.__init__` and `FeistelNumberStrategy.__init__` call `random.*`
at construction time (to pick Collatz parameters / Feistel salts). They gain
`rng` as a constructor argument instead:

```python
# Before
class CollatzStrategy(LoopObfuscationStrategy):
    def __init__(self, naming, start, stop, step):
        self.a = random.choice([3, 5])
        ...

# After
class CollatzStrategy(LoopObfuscationStrategy):
    def __init__(self, naming, start, stop, step, rng: random.Random):
        self.a = rng.choice([3, 5])
        ...
```

`LoopObfuscationStrategy.__init__` base signature gains `rng` too so the
pattern is uniform (even for `PlainStrategy`, which doesn't need it — it just
ignores the parameter).

Same for `NumberObscureStrategy.__init__(self, naming, rng)`.

### Injectors and transformers

Every injector / transformer that calls `random.*` directly, or that
instantiates a strategy, gains `rng: random.Random` in its constructor:

```python
# Before
JunkInjector(naming, strategy_classes, passes=1)
ConditionalInjector(naming, strategy_classes, chance)
IdentityFuncInjector(strategy, probability)
NumberObscurerInjector(naming, strategy)
Ob_For(naming, strategy_class)
Renamer(namespace)
```

```python
# After
JunkInjector(naming, strategy_classes, passes, rng)
ConditionalInjector(naming, strategy_classes, chance, rng)
IdentityFuncInjector(strategy, probability, rng)
NumberObscurerInjector(naming, strategy, rng)   # strategy already constructed with rng
Ob_For(naming, strategy_class, rng)
Renamer(namespace, rng)
```

Each injector stores `self.rng = rng` and passes it to strategies on every
call: `strat.get_junk(self.rng)`, `strat.wrap(expr, self.rng)`, etc.

### `MixedIdentityStrategy`

Currently holds `self._choices` and calls `random.choice(self._choices)` in
`wrap`. After the change, `wrap(self, expr, rng)` calls `rng.choice(self._choices)`.
`MixedIdentityStrategy.__init__` no longer needs to be special — the random
choice is deferred to call time.

---

## `pipeline.py` changes

Replace the `seeded()` context manager with direct `random.Random` construction:

```python
# Before
with _PIPELINE_LOCK:
    with seeded(cfg.seed):
        ...
        tree = JunkInjector(naming, selected, cfg.junk_density).apply(tree)

# After
with _PIPELINE_LOCK:
    rng = random.Random(cfg.seed)   # seed=None → non-deterministic, but isolated
    ...
    tree = JunkInjector(naming, selected, cfg.junk_density, rng).apply(tree)
```

`random.Random(None)` uses system entropy, identical behaviour to the current
unseeded path. `random.Random(42)` is fully deterministic and isolated from
the global RNG — so two concurrent API requests with different seeds no longer
interfere even without the lock. The lock can be removed once this lands.

`Utils/random_seeder.py` is no longer imported or used — delete it.

---

## Migration notes

- `random.getrandbits(n)` → `rng.getrandbits(n)`
- `random.choice(seq)` → `rng.choice(seq)`
- `random.choices(seq, k=n)` → `rng.choices(seq, k=n)`
- `random.randint(a, b)` → `rng.randint(a, b)`
- `random.sample(seq, k)` → `rng.sample(seq, k)`
- `random.random()` → `rng.random()`
- All `import random` at the top of strategy/injector files stay (the stdlib
  module is still needed for the `random.Random` type annotation); the global
  function calls are replaced.

---

## Verification

1. `python obfuscate.py --seed 42 --print` run twice → character-for-character
   identical output (both runs, same seed).
2. `python obfuscate.py --seed 42 --print` vs `POST /obfuscate` with `seed:42`
   → identical output (CLI and API now use the same isolated RNG).
3. Two concurrent API requests with different seeds produce the correct outputs
   for each seed with no cross-contamination.
4. `python obfuscate.py` with no `--seed` → different output each run
   (unseeded `random.Random()` uses system entropy).
5. `Utils/random_seeder.py` is gone; no import of it remains anywhere.
