# Plan: Test Suite

## Approach

Round-trip behavioral tests: run a fixture script through the obfuscator, execute both original and obfuscated output, assert stdout matches.

- Framework: `pytest`
- Fixture scripts in `tests/fixtures/` — small self-contained Python programs covering: basic arithmetic, loops, classes, imports, string literals, nested functions
- One parametrized test per fixture: `original_output == obfuscated_output`
- Seeded runs (`--seed`) for determinism so test output is stable across runs
- Separate unit tests for individual strategies where behavior is non-obvious (e.g. Collatz sequence validity, Feistel round-trip)

## Files Affected

- New: `tests/` directory with `test_roundtrip.py` and `fixtures/`
- `requirements.txt` — add `pytest`
