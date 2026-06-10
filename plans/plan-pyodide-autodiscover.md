# Plan: Pyodide Package Autodiscovery

## Current State

`scripts/build_package_json.py` and `infra/main.tf` each maintain a separate hardcoded list of Python files to bundle for Pyodide. They must be kept in sync manually. Recent plans (string obfuscation, bogus functions, import obfuscation, collatz seed) all added files to `build_package_json.py` but not to `main.tf`, causing the deployed Pyodide bundle to silently omit those modules.

## Approach

Replace both lists with a single auto-discovery step:

1. `build_package_json.py` globs all `*.py` files from a hardcoded list of package directories (`Encryption`, `Injectors`, `LoopObfuscation`, `NameTracker`, `Renaming`, `Utils`) plus `pipeline.py` at the repo root. `__init__.py` files are included; `__pycache__` is excluded.
2. It writes the discovered file list to `pyodide_files.json` at the repo root (sorted, for stable diffs).
3. It also continues to write `frontend/package.json` with file contents (unchanged behavior for local dev).
4. `infra/main.tf` replaces its hardcoded `pyodide_package_files` list with `jsondecode(file("${path.module}/../pyodide_files.json"))`.
5. `pyodide_files.json` is committed as a build artifact (like `frontend/package.json`).

Adding a new `.py` file to any bundled package is now automatically picked up the next time `make build-package` runs — no list to update.

## Files Affected

- `scripts/build_package_json.py` — replace hardcoded list with glob; write `pyodide_files.json` as a side effect
- `infra/main.tf` — replace `pyodide_package_files` list with `jsondecode(file(...))`
- `pyodide_files.json` — new generated file, committed to repo
