# Plan: Import Obfuscation

Replace explicit `import` statements with `__import__()` calls stored in variables, then rename those variables through the existing `Renamer` pass so the module names are hidden.

## Approach

- Add an `ImportObfuscator` AST transformer that visits `Import` and `ImportFrom` nodes
- `import foo` → `<renamed_var> = __import__('foo')`
- `import foo as bar` / `from foo import bar` → similar `__import__` + attribute access pattern
- All subsequent references to the imported name are already handled by `Renamer` since the binding becomes a normal variable assignment
- Insert the transformer into the pipeline before `Renamer`

## Files Affected

- New: `Injectors/import_obfuscator.py`
- `obfuscate.py` — add to pipeline
- `app.py` — add toggle to `ObfuscationConfig`
