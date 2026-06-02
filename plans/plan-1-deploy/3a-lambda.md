# 3a: Lambda Packaging

**Depends on:** 1b (shared pipeline)

## What

Package the pyobfuscate engine as an AWS Lambda function. The handler accepts the same JSON body as `POST /obfuscate` and returns the obfuscated source (or an error payload).

## Approach

- Handler: `lambda_handler(event, context)` in a new `lambda_handler.py`
  - Parse body as `ObfuscationConfig`
  - Call `run_pipeline(config)`
  - Return `{"statusCode": 200, "body": obfuscated_source}`
- Dependencies: only stdlib + the pyobfuscate package itself — no FastAPI/uvicorn needed in the Lambda zip
- Build: a `Makefile` or script (`scripts/build_lambda.sh`) that zips the package into `dist/lambda.zip`
- The Lambda runtime is Python 3.12

## Files

- New: `lambda_handler.py`
- New: `scripts/build_lambda.sh` — produces `dist/lambda.zip`

## Verification

1. `bash scripts/build_lambda.sh` completes without error, produces `dist/lambda.zip`
2. Install AWS SAM CLI or use Docker Lambda RIE: `sam local invoke` with a sample event JSON — response contains obfuscated source
3. Response for invalid input (e.g. syntax error in source) returns `{"statusCode": 400, ...}` rather than a 500
