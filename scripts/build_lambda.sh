#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$REPO_ROOT/dist"
ZIP="$DIST_DIR/lambda.zip"

mkdir -p "$DIST_DIR"
rm -f "$ZIP"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

cp "$REPO_ROOT/lambda_handler.py" "$TMP/"
cp "$REPO_ROOT/pipeline.py"       "$TMP/"

for pkg in Encryption Injectors LoopObfuscation NameTracker Renaming Utils; do
    cp -r "$REPO_ROOT/$pkg" "$TMP/"
done

python3 - "$TMP" "$ZIP" <<'EOF'
import sys, zipfile, pathlib

src_dir = pathlib.Path(sys.argv[1])
zip_path = pathlib.Path(sys.argv[2])

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(src_dir.rglob("*")):
        if path.suffix == ".pyc" or "__pycache__" in path.parts:
            continue
        if path.is_file():
            zf.write(path, path.relative_to(src_dir))

print(f"Built: {zip_path}  ({zip_path.stat().st_size // 1024} KB)")
EOF
