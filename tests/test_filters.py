from scripts.filters import should_include_video


def test_filter_cases() -> None:
    assert should_include_video(181, "none", 180, True, True)[0] is True
    assert should_include_video(180, "none", 180, True, True)[0] is False
    assert should_include_video(60, "live", 180, True, True)[0] is True
    assert should_include_video(None, "upcoming", 180, True, True)[0] is True
    assert should_include_video(None, "none", 180, True, True)[0] is False
