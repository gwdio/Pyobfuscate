# 1a: Strategy Registry

**Depends on:** nothing  
**Absorbed from:** plan-autodiscovery.md

## What

Add `__init_subclass__` to each strategy base class so that defining a subclass anywhere automatically registers it. Replace hardcoded strategy lists in `obfuscate.py` and `app.py` with registry lookups.

## Implementation

Each base class gets a class-level `_registry: dict[str, type]` and:

```python
def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)
    JunkInjectionStrategy._registry[cls.__name__] = cls
```

`obfuscate.py` and `app.py` then do `JunkInjectionStrategy._registry['ArithmeticStrategy']` instead of importing the class directly, and the API's strategy-selection fields accept names as strings (they already do via `ObfuscationConfig`).

Add a `GET /strategies` endpoint to `app.py` that returns all registered strategy names per phase — the frontend will need this.

## Files

- `Injectors/junk_strategies.py` — base class `JunkInjectionStrategy`
- `Injectors/junk_conditional_strategies.py` — base class `JunkConditionalStrategy`
- `Injectors/identity_strategies.py` — base class `IdentityFuncStrategy`
- `LoopObfuscation/obfuscation_strategies.py` — base class `LoopObfuscationStrategy`
- `Encryption/number_obscure_strategies.py` — base class `NumberObscureStrategy`
- `obfuscate.py` — replace hardcoded class references with registry lookups
- `app.py` — same, plus add `GET /strategies`

## Verification

1. `python obfuscate.py` on `IO/input.py` — output is still valid and behaviorally identical (run both, diff stdout)
2. In a scratch Python session, define a new subclass of any base — confirm it appears in `_registry` without touching any other file
3. `GET /strategies` returns a JSON object with all phase names and their registered strategy names
