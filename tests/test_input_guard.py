import pytest
from Utils.input_guard import _MAX_BYTES, _MAX_DEPTH, _MAX_LINES, validate_input


def test_valid_input_passes():
    validate_input("x = 1\n")


def test_at_byte_limit_passes():
    source = "x" * _MAX_BYTES
    validate_input(source)


def test_exceeds_byte_limit_raises():
    source = "x" * (_MAX_BYTES + 1)
    with pytest.raises(ValueError, match=str(_MAX_BYTES // 1000)):
        validate_input(source)


def test_at_line_limit_passes():
    source = "\n".join(["x = 1"] * _MAX_LINES)
    validate_input(source)


def test_exceeds_line_limit_raises():
    source = "\n".join(["x = 1"] * (_MAX_LINES + 1))
    with pytest.raises(ValueError, match=str(_MAX_LINES)):
        validate_input(source)


def test_at_depth_limit_passes():
    source = "(" * _MAX_DEPTH + "1" + ")" * _MAX_DEPTH
    validate_input(source)


def test_exceeds_depth_limit_raises():
    source = "(" * (_MAX_DEPTH + 1) + "1" + ")" * (_MAX_DEPTH + 1)
    with pytest.raises(ValueError, match=str(_MAX_DEPTH)):
        validate_input(source)


def test_brackets_and_braces_count_depth():
    source = "[" * (_MAX_DEPTH + 1) + "]" * (_MAX_DEPTH + 1)
    with pytest.raises(ValueError):
        validate_input(source)


def test_depth_inside_string_not_counted():
    source = f"x = '{'(' * (_MAX_DEPTH + 10)}'\n"
    validate_input(source)
