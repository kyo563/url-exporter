import pytest

from scripts.input_resolver import InputResolveError, resolve_input


def test_channel_id_direct_input() -> None:
    resolved = resolve_input("UCxxxxxxxxxxxxxxxxxxxxxx")
    assert resolved.kind == "channel"
    assert resolved.id == "UCxxxxxxxxxxxxxxxxxxxxxx"


def test_channel_id_url() -> None:
    resolved = resolve_input("https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxxxxxxxx")
    assert resolved.kind == "channel"
    assert resolved.id == "UCxxxxxxxxxxxxxxxxxxxxxx"


def test_handle_url() -> None:
    resolved = resolve_input("https://www.youtube.com/@samplehandle")
    assert resolved.kind == "channel"
    assert resolved.id == "@samplehandle"


def test_playlist_url() -> None:
    resolved = resolve_input("https://www.youtube.com/playlist?list=PLYb5VtgsMlnfJXP02qsvdr8UQzz7_iK4p")
    assert resolved.kind == "playlist"
    assert resolved.id == "PLYb5VtgsMlnfJXP02qsvdr8UQzz7_iK4p"


def test_watch_url_with_list_prefers_playlist() -> None:
    resolved = resolve_input("https://www.youtube.com/watch?v=ghAR1BncfmU&list=PLYb5VtgsMlnfJXP02qsvdr8UQzz7_iK4p")
    assert resolved.kind == "playlist"
    assert resolved.id == "PLYb5VtgsMlnfJXP02qsvdr8UQzz7_iK4p"


def test_invalid_input() -> None:
    with pytest.raises(InputResolveError):
        resolve_input("https://example.com")
