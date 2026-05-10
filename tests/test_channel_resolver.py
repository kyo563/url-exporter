import pytest

from scripts.channel_resolver import ChannelUrlError, parse_channel_url


def test_channel_id_url() -> None:
    ref = parse_channel_url("https://www.youtube.com/channel/UC1234567890123456789012")
    assert ref.kind == "channel_id"
    assert ref.value == "UC1234567890123456789012"


def test_handle_url() -> None:
    ref = parse_channel_url("https://www.youtube.com/@example_handle")
    assert ref.kind == "handle"
    assert ref.value == "example_handle"


def test_unsupported_url() -> None:
    with pytest.raises(ChannelUrlError):
        parse_channel_url("https://www.youtube.com/user/legacy")
