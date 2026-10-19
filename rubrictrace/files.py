"""Bounded regular JSON input; no duplicate fields, pipes or symlinks."""

import json
import math
import os
import stat
from pathlib import Path
from .core import Error


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Error("Duplicate JSON field")
        result[key] = value
    return result


def _valid_values(value, depth=0):
    if depth > 64:
        raise Error("JSON nesting exceeds 64 levels")
    if isinstance(value, str):
        value.encode("utf-8")
    elif isinstance(value, float) and not math.isfinite(value):
        raise Error("Non-finite JSON number")
    elif isinstance(value, dict):
        for key, item in value.items():
            _valid_values(key, depth + 1)
            _valid_values(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _valid_values(item, depth + 1)


def loads(raw):
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(Error("Non-finite JSON number")),
        )
        _valid_values(value)
        return value
    except (ValueError, RecursionError, UnicodeError):
        raise Error("Malformed or excessively nested JSON") from None


def read_json(path):
    try:
        path = Path(path)
        if path.is_symlink():
            raise Error("Input must not be a symlink")
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as f:
            st = os.fstat(f.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_size > 2_000_000:
                raise Error("Input must be a regular JSON file at most 2 MB")
            data = f.read(2_000_001)
        if len(data) > 2_000_000:
            raise Error("Input exceeds 2 MB")
        return loads(data.decode("utf-8"))
    except (OSError, UnicodeError):
        raise Error("Cannot read regular UTF-8 JSON input") from None
