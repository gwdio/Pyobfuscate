# Plan: String Literal Obfuscation

## Current State

`NumberObscurerInjector.visit_Constant` explicitly skips non-integers — string literals pass through the entire pipeline untouched.

## Approach

Add a `StringObfuscator` transformer (parallel to `NumberObscurerInjector`) with pluggable strategies:

- **XOR strategy**: encode string as a list of XOR'd integer literals, inject a decoder lambda/function, replace the literal with a call to it
- **Char array strategy**: replace `"hello"` with `chr(104)+chr(101)+...` (works without a helper function)
- Visit `ast.Constant` nodes where `isinstance(node.value, str)`, skip docstrings (first statement of module/class/function bodies) to avoid breaking tools that read them

Insert into the pipeline after `NumberObscurerInjector` so numeric literals in the encoded output can also be obscured.

## Files Affected

- New: `Encryption/string_obscurer.py`
- New: `Encryption/string_obscure_strategies.py`
- `obfuscate.py` — add to pipeline
- `app.py` — add toggle and strategy selection to `ObfuscationConfig`
