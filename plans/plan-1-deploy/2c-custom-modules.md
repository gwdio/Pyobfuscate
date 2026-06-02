# 2c: Custom Module Upload (Client-Side)

**Depends on:** 2b (Pyodide must be running), 1a (registry must exist)

## What

Let users upload their own `.py` files defining strategy subclasses. The uploaded file is loaded into Pyodide, its classes self-register via the registry, and they appear immediately in the relevant stage dropdowns.

## Approach

1. Add a file input (or drag-drop zone) to the frontend, labelled "Upload custom strategy"
2. On file select: read the file as text, write it into Pyodide's FS under a known path, then `importlib.import_module` it from within Pyodide — the `__init_subclass__` hook registers it automatically
3. After import, call `GET /strategies` equivalent against the in-browser registry to refresh the strategy dropdowns
4. Show a validation error in the UI if the file fails to import or defines no subclasses of a known base

Client-only — the Lambda path does not accept custom modules.

## Files

- `frontend/app.js` — file input handler, Pyodide FS write + import call, dropdown refresh
- `frontend/index.html` — file input element, validation message area

## Verification

1. Write a minimal custom strategy (e.g. a `JunkInjectionStrategy` subclass that emits `pass`) and upload it
2. The strategy name appears in the junk strategy dropdown
3. Select it, run obfuscation — output contains `pass` statements from the custom strategy
4. Upload a file that is not a valid strategy — UI shows a clear error, no crash
5. Switch to Server mode — file input is hidden or disabled (not applicable to Lambda path)
