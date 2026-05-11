from __future__ import annotations


def should_include_video(
    duration_sec: int | None,
    live_broadcast_content: str | None,
    shorts_duration_threshold_sec: int,
    include_active_live: bool,
    include_upcoming_live: bool,
    exclude_shorts: bool = True,
) -> tuple[bool, str]:
    live_state = (live_broadcast_content or "none").lower()

    if live_state == "live" and include_active_live:
        return True, ""
    if live_state == "upcoming" and include_upcoming_live:
        return True, ""

    if duration_sec is None:
        return False, "duration_missing"

    if exclude_shorts and duration_sec <= shorts_duration_threshold_sec:
        return False, "short_like_duration"

    return True, ""
