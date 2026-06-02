# Plan 1: Big Deploy — Index

Add a web frontend, hybrid client (Pyodide) / server (Lambda) execution, custom strategy module support, configurable pipeline sequencing, and IaC for the full stack.

---

## Execution Order

```
1a  Strategy Registry
 └─ 1b  Shared Pipeline
     ├─ 1c  CLI Argparse
     ├─ 1d  (pipeline sequencing is part of 1b)
     └─ 3a  Lambda Packaging
         └─ 3b  Lambda Hardening
             └─ 3c  IaC
                 └─ 4a  Frontend — Connect Both Paths
                         ▲
2a  Frontend Shell
 └─ 2b  Pyodide Integration ──────────────────────┘
     └─ 2c  Custom Module Upload
```

Steps 2a–2c and steps 1b→3a–3c are independent tracks that can be worked in parallel once 1a and 1b are done.

---

## Steps

| Step | File | What | Hard deps |
|------|------|------|-----------|
| 1a | `1a-strategy-registry.md` | `__init_subclass__` registry on all strategy bases; `GET /strategies` endpoint | — |
| 1b | `1b-shared-pipeline.md` | Extract `run_pipeline()` into `pipeline.py`; add `stage_order` to config | 1a |
| 1c | `1c-cli-argparse.md` | `argparse` in `obfuscate.py`, delegates to `run_pipeline` | 1b |
| 2a | `2a-frontend-shell.md` | Static HTML/JS/CSS shell: editor, output pane, module controls (stub) | 1a (for strategy names) |
| 2b | `2b-pyodide-integration.md` | Load pyobfuscate wheel in browser; client-side execution path | 2a |
| 2c | `2c-custom-modules.md` | Upload `.py` strategy files into Pyodide, auto-register, populate dropdowns | 2b, 1a |
| 3a | `3a-lambda.md` | `lambda_handler.py` + build script producing `dist/lambda.zip` | 1b |
| 3b | `3b-lambda-hardening.md` | Input validation, timeout wrapper, surface audit | 3a |
| 3c | `3c-iac.md` | Terraform/CDK: Lambda, Function URL, S3, CloudFront | 3a, 3b |
| 4a | `4a-frontend-connect.md` | Wire server path in UI; CORS; disable custom modules in server mode | 2b, 3c |

---

## Absorbed Plans

- `plan-autodiscovery.md` → covered by **1a**
- `plan-cli-improvement.md` → covered by **1b** + **1c**

Those standalone plan files have been removed.
