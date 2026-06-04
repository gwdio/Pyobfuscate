# 2b: Pyodide Integration (Client Execution)

**Depends on:** 2a

## What

Load the pyobfuscate engine into the browser via Pyodide so obfuscation runs entirely client-side with no server round-trip. Wire the Submit button to this path when "Client" is selected.

## Approach

1. Load Pyodide from CDN in `app.js` on page load (show a spinner while it initialises)
2. Write the pyobfuscate package files into Pyodide's virtual FS — either bundle them as a wheel (preferred, use `python -m build` to produce a `.whl`) or write each `.py` file directly via `pyodide.FS.writeFile`
3. `await pyodide.runPythonAsync(...)` to call `run_pipeline(config)` with the config constructed from the UI state
4. Display the returned string in the output pane

The wheel approach is cleaner: add a `pyproject.toml`, build once, host alongside the frontend, fetch + `micropip.install` at runtime.

## Files

- New: `pyproject.toml` — package metadata so the project can be built as a wheel
- `frontend/app.js` — Pyodide load + init, client-side execute path
- `frontend/index.html` — add Pyodide CDN script tag

## Verification

1. Open frontend, wait for Pyodide to load (spinner disappears)
2. Paste valid Python into input, select Client mode, click Submit — result appears with no network request visible in DevTools Network tab
3. Paste intentionally broken Python — error is caught and displayed in the UI rather than crashing the page
4. Check DevTools console — no uncaught exceptions during normal operation
