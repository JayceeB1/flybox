"""Lossless biological identifier helpers for connectome normalization."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import numpy as np
import numpy.typing as npt


class BiologicalIdError(ValueError):
    """A biological identifier could not be represented losslessly."""


def exact_uint64_ids(values: Iterable[Any] | npt.NDArray[Any]) -> npt.NDArray[np.uint64]:
    """Convert integer/decimal-string IDs to uint64 without any float round-trip."""

    if isinstance(values, np.ndarray):
        if values.ndim != 1:
            raise BiologicalIdError("biological ID array must be one-dimensional")
        if values.dtype.kind in "iu":
            if values.dtype.kind == "i" and np.any(values < 0):
                raise BiologicalIdError("negative biological IDs are forbidden")
            return values.astype(np.uint64, copy=False)
        if values.dtype.kind == "f":
            raise BiologicalIdError("floating-point IDs are forbidden")
        iterable: Iterable[Any] = values.tolist()
    else:
        iterable = values

    result: list[int] = []
    for index, value in enumerate(iterable):
        if isinstance(value, bool):
            raise BiologicalIdError(f"ID[{index}]: booleans are not biological IDs")
        if isinstance(value, (float, np.floating)):
            raise BiologicalIdError(f"ID[{index}]: floating-point IDs are forbidden")
        if isinstance(value, (int, np.integer)):
            number = int(value)
        elif isinstance(value, str) and value.isascii() and value.isdecimal():
            number = int(value, 10)
        else:
            raise BiologicalIdError(
                f"ID[{index}]: expected non-negative integer or decimal string"
            )
        if number < 0 or number > np.iinfo(np.uint64).max:
            raise BiologicalIdError(f"ID[{index}]: outside uint64 range")
        result.append(number)
    return np.asarray(result, dtype=np.uint64)


def require_unique_sorted(ids: npt.NDArray[np.uint64]) -> npt.NDArray[np.uint64]:
    """Return stable sorted IDs and reject duplicates."""

    if ids.ndim != 1:
        raise BiologicalIdError("biological ID array must be one-dimensional")
    ordered = np.sort(ids, kind="stable")
    if len(ordered) and np.any(ordered[1:] == ordered[:-1]):
        raise BiologicalIdError("duplicate biological IDs are forbidden")
    return ordered


def json_id(value: int | np.integer[Any]) -> str:
    """Serialize one biological ID for JSON without JavaScript precision loss."""

    number = int(value)
    if number < 0 or number > np.iinfo(np.uint64).max:
        raise BiologicalIdError("biological ID outside uint64 range")
    return str(number)
