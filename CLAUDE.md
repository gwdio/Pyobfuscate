# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

**CLI mode** — reads `IO/input.py`, writes `IO/output.py`:
```bash
python obfuscate.py
# or
python -m pyobfuscate
```

**API mode** — FastAPI server on port 8000:
```bash
uvicorn app:app --reload
# POST /obfuscate  with JSON body matching ObfuscationConfig
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

## Testing

Run the automated round-trip test suite:
```bash
pip install -r requirements-dev.txt   # includes pytest
pytest
```

Manual verification:
```bash
python IO/input.py > original.out
python IO/output.py > obfuscated.out
diff original.out obfuscated.out   # should be empty — same runtime behavior
```

## Architecture

pyobfuscate transforms Python source code into a functionally equivalent but obfuscated version by operating on the AST.

### Pipeline

Both the CLI (`obfuscate.py`) and API (`app.py`) run the same ordered pipeline:

1. `ast.parse()` — source → AST
2. `Naming.analyze()` — collect all identifiers for collision avoidance
3. `JunkInjector` — insert meaningless statements (30% per insertion point)
4. `Ob_For` — convert `for` loops to `while` loops with complex iteration logic
5. `ConditionalInjector` — wrap statements in always-true conditionals (30% chance)
6. `IdentityFuncInjector` — wrap expressions in identity operations (e.g., `1 and x`)
7. `NumberObscurerInjector` (×2 passes) — encode integer literals with cipher strategies
8. `Renamer` — replace all user-defined names with random 8-char identifiers
9. `ast.unparse()` — AST → obfuscated source string

### Strategy Pattern

Every obfuscation phase uses pluggable strategies. Each module has a `*Strategy` base class and concrete implementations. The API exposes strategy selection via `ObfuscationConfig`; the CLI uses hardcoded selections.

Key strategy families:
- **Junk**: `ArithmeticStrategy`, `BitwiseStrategy`, `LambdaStrategy`, `NonConstantTimeStrategy`
- **Loop**: `PlainStrategy` (straightforward for→while), `CollatzStrategy` (Collatz-like state machine)
- **Identity**: `DefaultIdentityFuncStrategy` (`1 and x`), `OrIdentityStrategy`
- **Number**: `FeistelNumberStrategy` (4-round Feistel cipher), `XorStringNumberStrategy`

### Key Modules

| Module | Responsibility |
|--------|---------------|
| `NameTracker/naming.py` | Tracks all identifiers in the AST; `get_name(base)` generates unique names |
| `Renaming/renamer.py` | Two-pass rewrite: collect all defined names, then rewrite all references |
| `Injectors/inject_junk.py` | Injects junk statements into Module and FunctionDef bodies |
| `Injectors/identity_injector.py` | Wraps `Name` and `Constant` nodes in identity operations |
| `Injectors/conditional_injector.py` | Wraps statements in opaque always-true predicates |
| `LoopObfuscation/ob_for.py` | Orchestrates for→while: unwraps nested loops, then applies strategy |
| `Encryption/number_obscurer.py` | Visits `ast.Constant` int nodes and replaces with encoded expressions |

### Concurrency

The API wraps pipeline execution in `_PIPELINE_LOCK` (threading lock) to prevent concurrent requests from corrupting shared RNG state.

## Active Development

Planned work is tracked in `plans/`. Completed plans (merged to main): deploy, randomness, renamer-fix, testing, ui-improvements, pipeline-recipe, usability-docs, plan-3-collatz-linear, plan-4-collatz-seed, plan-depth-size-guard.

Remaining plans:

- `plans/plan-import-obfuscation.md` — obfuscate `import` statements
- `plans/plan-string-obfuscation.md` — obfuscate string literals
- `plans/plan-bogus-functions.md` — inject dead functions at module level

## Branch Convention

- One branch per plan: `plan/3-collatz-linear`, `plan/4-collatz-seed`, `plan/string-obfuscation`, etc.
- All deploy subplans (`plan-1-deploy/`) share a single long-running branch: `deploy`
- `main` receives merges only when a plan is fully verified

### API Config (`app.py`)

`ObfuscationConfig` (Pydantic) exposes:
- `phase_configs: list[{type, config}]` — ordered phase list; when set, drives the pipeline (frontend always sends this)
- Legacy flat fields (CLI path): per-phase toggles `enable_*`, strategy lists, `junk_density`, `identity_probability`
- `seed` (optional int for reproducibility)
- `input_path`, `output_path`, `return_code`
