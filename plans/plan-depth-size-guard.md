# Plan: Input Depth/Size Guard

## Problem

Very large or deeply nested inputs can cause quadratic behavior in Python's own parser and in AST visitors. No validation exists before `ast.parse()` is called.

## Approach

Add a validation step before `ast.parse()` in both `obfuscate.py` and `app.py`:
- Line count limit (e.g. 5000 lines) — simple `len(source.splitlines())`
- Nesting depth limit — lightweight pre-parse scan counting indent level or bracket depth
- Raise a clear error with the limit that was exceeded

Exact limits TBD based on profiling, but should be enforced at the API boundary especially given the Lambda deployment in plan-1-deploy.md.

## Files Affected

- New: `Utils/input_guard.py` — `validate_input(source: str)` raises `ValueError` on violation
- `obfuscate.py` and `app.py` — call before `ast.parse()`
