# Plan: Bogus Function Injection [DONE]

## Current State

`JunkInjector` inserts junk statements inside existing function bodies. There is no mechanism to inject entirely new, never-called functions at module level.

## Approach

Add a `BogusFunction Injector` that runs after `JunkInjector` and injects plausible-looking dead functions at module scope:

- Generate function signatures with random names (via `Naming.get_name`) and 1–3 parameters
- Bodies are composed of the existing junk strategies so they look internally consistent
- Functions are never called — they exist purely to inflate the apparent complexity of the module
- Injection density configurable (number of bogus functions per N real functions)

Renamer will handle name obfuscation of both the function name and its internal variables in the existing pass.

## Files Affected

- New: `Injectors/bogus_function_injector.py`
- `obfuscate.py` — add to pipeline (after `JunkInjector`, before `Renamer`)
- `app.py` — add toggle to `ObfuscationConfig`
