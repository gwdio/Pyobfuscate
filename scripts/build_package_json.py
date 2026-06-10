#!/usr/bin/env python3
"""Generate frontend/package.json — the static bundle Pyodide fetches client-side.

Run this whenever any file in _PACKAGE_FILES changes, before deploying.
The file is committed so Terraform's S3 upload picks it up without a server round-trip.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).parent.parent

PACKAGE_FILES = [
    "pipeline.py",
    "Encryption/__init__.py",
    "Encryption/number_obscure_strategies.py",
    "Encryption/number_obscurer.py",
    "Encryption/string_obscure_strategies.py",
    "Encryption/string_obscurer.py",
    "Injectors/__init__.py",
    "Injectors/bogus_function_injector.py",
    "Injectors/conditional_injector.py",
    "Injectors/identity_injector.py",
    "Injectors/identity_strategies.py",
    "Injectors/import_obfuscator.py",
    "Injectors/inject_junk.py",
    "Injectors/junk_conditional_strategies.py",
    "Injectors/junk_strategies.py",
    "LoopObfuscation/__init__.py",
    "LoopObfuscation/collatz_seed.py",
    "LoopObfuscation/for_to_while_generic.py",
    "LoopObfuscation/loop_simplifier.py",
    "LoopObfuscation/ob_for.py",
    "LoopObfuscation/obfuscation_strategies.py",
    "NameTracker/__init__.py",
    "NameTracker/naming.py",
    "Renaming/__init__.py",
    "Renaming/renamer.py",
    "Utils/__init__.py",
]

missing = [f for f in PACKAGE_FILES if not (REPO / f).exists()]
if missing:
    print(f"ERROR: missing source files: {missing}", file=sys.stderr)
    sys.exit(1)

pkg = {rel: (REPO / rel).read_text(encoding="utf-8") for rel in PACKAGE_FILES}
out = REPO / "frontend" / "package.json"
out.write_text(json.dumps(pkg), encoding="utf-8")
print(f"Generated {out.relative_to(REPO)}  ({out.stat().st_size:,} bytes, {len(pkg)} files)")
