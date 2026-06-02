# 4a: Frontend — Connect Both Execution Paths

**Depends on:** 2b (Pyodide path working), 3c (Lambda deployed and URL known)

## What

Wire the execution path toggle so both paths are fully functional from the same UI.

## Client path (already done in 2b)
- No changes needed; verify still works end-to-end after frontend changes in this step

## Server path
- Read the Lambda Function URL from a config constant at the top of `app.js` (or a `/config` endpoint served by the CloudFront origin)
- On submit (Server mode): POST the config JSON to the Lambda Function URL, await response, display result
- Show a loading indicator while the request is in flight
- On error (4xx/5xx/network failure): display a human-readable message in the output pane, don't swallow the error silently

## CORS
- Lambda Function URL needs `AllowOrigins` set to the CloudFront domain (configured in 3c IaC)
- No CORS needed for the Pyodide path (client-side, no cross-origin request)

## Custom modules
- Disable the custom module upload control when Server mode is selected (server path does not accept custom modules)
- Show a tooltip explaining why

## Files

- `frontend/app.js` — server path submit handler, loading state, error display, toggle-aware custom module control
- `infra/` — ensure Lambda Function URL CORS config matches CloudFront domain

## Verification

1. Select Server mode, submit valid Python — result appears, Network tab shows one POST to the Lambda URL
2. Select Client mode, submit valid Python — result appears, no network request in Network tab
3. Switch modes mid-session — both paths still work independently
4. Server mode with Lambda returning 400 — error message displayed in output pane
5. Server mode, upload custom module button is disabled with tooltip
