import subprocess
import sys
from pathlib import Path

import pytest

from pipeline import ObfuscationConfig, run_pipeline

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES = sorted(
    p for p in FIXTURES_DIR.glob("*.py") if not p.name.startswith("_")
)


def _run(path: Path) -> str:
    return subprocess.check_output([sys.executable, str(path)], text=True)


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
def test_roundtrip(fixture, tmp_path):
    cfg = ObfuscationConfig(input_path=fixture, seed=42, return_code=True)
    obfuscated = run_pipeline(cfg)
    out_file = tmp_path / "out.py"
    out_file.write_text(obfuscated, encoding="utf-8")
    assert _run(fixture) == _run(out_file)


def test_feistel_roundtrip(tmp_path):
    src = tmp_path / "nums.py"
    values = [0, 1, 127, 128, 255, 1000, 65535, 2**20]
    src.write_text("\n".join(f"print({v})" for v in values), encoding="utf-8")
    cfg = ObfuscationConfig(
        input_path=src,
        seed=7,
        return_code=True,
        enable_junk=False,
        enable_loops=False,
        enable_conditionals=False,
        enable_identities=False,
        enable_renaming=False,
        number_strategies=["FeistelNumberStrategy"],
    )
    obfuscated = run_pipeline(cfg)
    out_file = tmp_path / "out.py"
    out_file.write_text(obfuscated, encoding="utf-8")
    assert _run(src) == _run(out_file)


def test_char_array_roundtrip(tmp_path):
    src = tmp_path / "strs.py"
    src.write_text(
        "x = 'hello'\ny = 'world'\nprint(x + ' ' + y)\n"
        "z = 'line one\\nline two'\nprint(z)\n"
        "words = ['alpha', 'beta', 'gamma']\nprint(', '.join(words))\n",
        encoding="utf-8",
    )
    cfg = ObfuscationConfig(
        input_path=src,
        seed=7,
        return_code=True,
        enable_junk=False,
        enable_loops=False,
        enable_conditionals=False,
        enable_identities=False,
        enable_numbers=False,
        enable_strings=True,
        enable_renaming=False,
        string_strategies=["CharArrayStrategy"],
    )
    obfuscated = run_pipeline(cfg)
    out_file = tmp_path / "out.py"
    out_file.write_text(obfuscated, encoding="utf-8")
    assert _run(src) == _run(out_file)


def test_xor_string_roundtrip(tmp_path):
    src = tmp_path / "strs_xor.py"
    src.write_text(
        "x = 'hello'\ny = 'world'\nprint(x + ' ' + y)\n"
        "z = 'Héllo wörld'\nprint(z)\n",
        encoding="utf-8",
    )
    cfg = ObfuscationConfig(
        input_path=src,
        seed=13,
        return_code=True,
        enable_junk=False,
        enable_loops=False,
        enable_conditionals=False,
        enable_identities=False,
        enable_numbers=False,
        enable_strings=True,
        enable_renaming=False,
        string_strategies=["XorStringStrategy"],
    )
    obfuscated = run_pipeline(cfg)
    out_file = tmp_path / "out.py"
    out_file.write_text(obfuscated, encoding="utf-8")
    assert _run(src) == _run(out_file)


def test_string_docstring_preserved(tmp_path):
    src = tmp_path / "docstrings.py"
    src.write_text(
        '"""Module docstring."""\n\n'
        'def greet(name):\n'
        '    """Return greeting."""\n'
        '    return "Hello, " + name\n\n'
        'print(greet("World"))\n'
        'print(greet.__doc__)\n',
        encoding="utf-8",
    )
    cfg = ObfuscationConfig(
        input_path=src,
        seed=1,
        return_code=True,
        enable_junk=False,
        enable_loops=False,
        enable_conditionals=False,
        enable_identities=False,
        enable_numbers=False,
        enable_strings=True,
        enable_renaming=False,
        string_strategies=["CharArrayStrategy"],
    )
    obfuscated = run_pipeline(cfg)
    out_file = tmp_path / "out.py"
    out_file.write_text(obfuscated, encoding="utf-8")
    assert _run(src) == _run(out_file)


def test_collatz_iteration_count(tmp_path):
    n = 8
    src = tmp_path / "loop.py"
    src.write_text(f"for i in range({n}):\n    print(i)\n", encoding="utf-8")
    cfg = ObfuscationConfig(
        input_path=src,
        seed=13,
        return_code=True,
        enable_junk=False,
        enable_conditionals=False,
        enable_identities=False,
        enable_numbers=False,
        enable_renaming=False,
        loop_strategy="CollatzStrategy",
    )
    obfuscated = run_pipeline(cfg)
    out_file = tmp_path / "out.py"
    out_file.write_text(obfuscated, encoding="utf-8")
    expected = "\n".join(str(i) for i in range(n)) + "\n"
    assert _run(out_file) == expected
