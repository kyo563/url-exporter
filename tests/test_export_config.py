from scripts.export_urls import parse_channels


def test_parse_channels_empty_yaml() -> None:
    channels, err = parse_channels({})
    assert channels == []
    assert "channels" in (err or "")


def test_parse_channels_empty_list() -> None:
    channels, err = parse_channels({"channels": []})
    assert channels == []
    assert "non-empty" in (err or "")


def test_parse_channels_missing_name() -> None:
    channels, err = parse_channels({"channels": [{"url": "https://www.youtube.com/@a"}]})
    assert channels == []
    assert "name" in (err or "")


def test_parse_channels_missing_url() -> None:
    channels, err = parse_channels({"channels": [{"name": "a"}]})
    assert channels == []
    assert "url" in (err or "")
