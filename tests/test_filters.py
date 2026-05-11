from scripts.filters import should_include_video


def test_filter_cases() -> None:
    assert should_include_video(181, "none", 180, True, True)[0] is True
    assert should_include_video(180, "none", 180, True, True)[0] is False
    assert should_include_video(60, "live", 180, True, True)[0] is True
    assert should_include_video(None, "upcoming", 180, True, True)[0] is True
    assert should_include_video(None, "none", 180, True, True)[0] is False


def test_exclude_shorts_false_keeps_short_video() -> None:
    included, reason = should_include_video(30, "none", 180, True, True, exclude_shorts=False)
    assert included is True
    assert reason == ""


def test_exclude_shorts_false_still_excludes_duration_missing() -> None:
    included, reason = should_include_video(None, "none", 180, True, True, exclude_shorts=False)
    assert included is False
    assert reason == "duration_missing"


def test_live_excluded_even_when_duration_missing_or_long() -> None:
    included, reason = should_include_video(None, "live", 180, False, True)
    assert included is False
    assert reason == "active_live_excluded"

    included, reason = should_include_video(9999, "live", 180, False, True)
    assert included is False
    assert reason == "active_live_excluded"


def test_upcoming_excluded_even_when_duration_missing_or_long() -> None:
    included, reason = should_include_video(None, "upcoming", 180, True, False)
    assert included is False
    assert reason == "upcoming_live_excluded"

    included, reason = should_include_video(9999, "upcoming", 180, True, False)
    assert included is False
    assert reason == "upcoming_live_excluded"


def test_live_and_upcoming_included_when_include_flags_enabled() -> None:
    included_live, reason_live = should_include_video(None, "live", 180, True, False)
    assert included_live is True
    assert reason_live == ""

    included_upcoming, reason_upcoming = should_include_video(None, "upcoming", 180, False, True)
    assert included_upcoming is True
    assert reason_upcoming == ""
