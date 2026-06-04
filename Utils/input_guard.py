_MAX_BYTES = 50_000
_MAX_LINES = 2_000
_MAX_DEPTH = 200


def validate_input(source: str) -> None:
    if len(source.encode("utf-8")) > _MAX_BYTES:
        raise ValueError(f"Source exceeds maximum size of {_MAX_BYTES // 1000} KB")
    if len(source.splitlines()) > _MAX_LINES:
        raise ValueError(f"Source exceeds maximum of {_MAX_LINES} lines")
    _check_nesting_depth(source)


def _check_nesting_depth(source: str) -> None:
    openers = {'(', '[', '{'}
    closers = {')', ']', '}'}
    depth = 0
    in_single = False
    in_double = False
    i = 0
    while i < len(source):
        ch = source[i]
        # Rough string literal skipping (handles common cases)
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if ch in openers:
                depth += 1
                if depth > _MAX_DEPTH:
                    raise ValueError(f"Source exceeds maximum nesting depth of {_MAX_DEPTH}")
            elif ch in closers:
                depth -= 1
        i += 1
