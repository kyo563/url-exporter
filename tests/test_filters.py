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
