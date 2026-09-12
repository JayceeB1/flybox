"""License identifiers used by FlyBox provenance records.

This module does not decide legal compatibility. It only keeps identifiers
canonical and machine-checkable so upstream terms are never silently erased.
"""

from __future__ import annotations

import re

_SPDX_LIKE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]*$")


def validate_license_id(value: str) -> str:
    """Return a canonical identifier or raise ValueError for malformed input."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("license identifier must be a non-empty string")
    canonical = value.strip()
    if _SPDX_LIKE.fullmatch(canonical) is None:
        raise ValueError(f"invalid license identifier: {value!r}")
    return canonical
