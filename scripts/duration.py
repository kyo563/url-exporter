from __future__ import annotations

import re

_DURATION_PATTERN = re.compile(r"^P(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)$")


def parse_iso8601_duration_to_seconds(value: str) -> int | None:
    if not isinstance(value, str):
        return None

    match = _DURATION_PATTERN.match(value)
    if not match:
        return None

    hours, minutes, seconds = match.groups()
    if hours is None and minutes is None and seconds is None:
        return None

    return int(hours or 0) * 3600 + int(minutes or 0) * 60 + int(seconds or 0)
