# 1c: CLI Argparse

**Depends on:** 1b (shared pipeline must exist first)  
**Absorbed from:** plan-cli-improvement.md

## What

Replace the hardcoded pipeline in `obfuscate.py` with `argparse`. Parse arguments into an `ObfuscationConfig` and delegate to `run_pipeline`.

## Arguments to Expose

| Flag | Maps to |
|------|---------|
| `--input` | `input_path` (default: `IO/input.py`) |
| `--output` | `output_path` (default: `IO/output.py`) |
| `--seed` | `seed` |
| `--no-junk`, `--no-loops`, `--no-conditionals`, `--no-identities`, `--no-numbers`, `--no-renaming` | per-phase enable flags |
| `--junk-density` | `junk_density` (1–5) |
| `--identity-prob` | `identity_probability` (0.0–1.0) |
| `--stages` | `stage_order` (space-separated list) |
| `--junk-strategies`, `--loop-strategy`, etc. | per-phase strategy selection |
| `--print` | `return_code` — print result to stdout instead of writing file |

## Files

- `obfuscate.py` — replace `main()` body with argparse + `run_pipeline` call

## Verification

1. `python obfuscate.py --no-loops --no-renaming --seed 42 --print` — output should have no loop obfuscation and no renamed identifiers
2. `python obfuscate.py --help` — all flags listed and described
3. `python obfuscate.py` with no args produces same result as before (defaults preserved)
