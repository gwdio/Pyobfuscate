# 1b: Shared Pipeline Module

**Depends on:** 1a (registry must exist before pipeline can resolve strategies by name)

## What

Extract the pipeline execution logic — currently duplicated between `obfuscate.py` and `app.py` — into a single `pipeline.py` module. Both the CLI and API construct an `ObfuscationConfig` and call `run_pipeline(config) -> str`.

Also make pipeline stage order configurable: `ObfuscationConfig` gains an optional `stage_order: list[str]` field. When absent, the default order is used. Stages are identified by short names (`junk`, `loops`, `conditionals`, `identities`, `numbers`, `renaming`). The pipeline iterates `stage_order` and skips any stage whose enable flag is False.

## Files

- New: `pipeline.py` — `run_pipeline(config: ObfuscationConfig) -> str`
- `obfuscate.py` — parse args (see 1c), construct config, call `run_pipeline`
- `app.py` — POST handler calls `run_pipeline`; remove duplicated pipeline code
- `app.py` — add `stage_order` to `ObfuscationConfig`

## Verification

1. Call CLI and API with identical config and seed on the same input — outputs must be character-for-character identical
2. Pass `stage_order: ["renaming", "junk"]` (only two stages, reversed) via the API — confirm only those two run and in that order (check the output lacks loop/number obfuscation)
