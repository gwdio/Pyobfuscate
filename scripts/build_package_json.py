#!/usr/bin/env python3
"""Generate frontend/package.json and pyodide_files.json.

Auto-discovers all *.py files in the bundled packages plus pipeline.py.
Both output files are committed so Terraform and local dev stay in sync
without a separate list to maintain.
"""
import json
import pathlib

REPO = pathlib.Path(__file__).parent.parent

PACKAGE_DIRS = ["Encryption", "Injectors", "LoopObfuscation", "NameTracker", "Renaming", "Utils"]

files = sorted(
    ["pipeline.py"] + [
        str(p.relative_to(REPO))
        for d in PACKAGE_DIRS
        for p in sorted((REPO / d).glob("*.py"))
    ]
)

pkg = {rel: (REPO / rel).read_text(encoding="utf-8") for rel in files}

files_out = REPO / "pyodide_files.json"
files_out.write_text(json.dumps(files, indent=2), encoding="utf-8")
print(f"Generated {files_out.relative_to(REPO)}  ({len(files)} files)")

pkg_out = REPO / "frontend" / "package.json"
pkg_out.write_text(json.dumps(pkg), encoding="utf-8")
print(f"Generated {pkg_out.relative_to(REPO)}  ({pkg_out.stat().st_size:,} bytes)")
