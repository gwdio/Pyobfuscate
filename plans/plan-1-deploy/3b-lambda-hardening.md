# 3b: Lambda Hardening

**Depends on:** 3a

## What

Restrict what the Lambda execution environment can do, and validate inputs before they reach the pipeline.

## Mitigations

### Input validation (ties into plan-depth-size-guard.md)
- Enforce before `ast.parse()`: max source length (e.g. 50 KB), max line count (e.g. 2000), max nesting depth (bracket scan)
- Return HTTP 400 with a descriptive message on violation

### Execution timeout
- Wrap `run_pipeline` in a `concurrent.futures.ThreadPoolExecutor` with a timeout (e.g. 10s)
- Return HTTP 408 on timeout rather than letting Lambda hit its own hard limit with a 500

### IAM role (defined in 3c IaC, noted here for awareness)
- No VPC, no S3, no other AWS services — Lambda role needs only `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

### No outbound network / filesystem writes
- Lambda's `/tmp` is writable — ensure the pipeline never writes there (currently it doesn't, but verify)
- No `subprocess`, `socket`, or `os.system` calls reachable from the pipeline — confirm by grepping the codebase

### Seccomp / deeper sandboxing
- Deferred: evaluate if AST manipulation vulnerabilities are found in practice; Lambda's default isolation may be sufficient initially

## Files

- New: `Utils/input_guard.py` (can share with plan-depth-size-guard.md)
- `lambda_handler.py` — add timeout wrapper, call `validate_input` before pipeline

## Verification

1. Send a payload with 100k lines — Lambda returns 400, not a timeout or 500
2. Send a deeply nested payload (e.g. 1000 nested function calls) — returns 400
3. Send a valid payload — returns 200 within the timeout window
4. Check CloudWatch logs — no errors, execution time logged
