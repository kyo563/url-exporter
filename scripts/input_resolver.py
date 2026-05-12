from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from scripts.channel_resolver import ChannelUrlError, parse_channel_url


class InputResolveError(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedInput:
    kind: str
    id: str


def _is_channel_id(text: str) -> bool:
    return text.startswith("UC") and len(text) == 24


def resolve_input(input_text: str) -> ResolvedInput:
    text = (input_text or "").strip()
    if not text:
        raise InputResolveError("Input is empty")

    if _is_channel_id(text):
        return ResolvedInput(kind="channel", id=text)

    parsed = urlparse(text)
    host = (parsed.netloc or "").lower()
    if host in {"youtube.com", "www.youtube.com"}:
        query = parse_qs(parsed.query)
        playlist_ids = query.get("list", [])
        if playlist_ids and playlist_ids[0]:
            return ResolvedInput(kind="playlist", id=playlist_ids[0])

    try:
        ref = parse_channel_url(text)
    except ChannelUrlError as e:
        raise InputResolveError(str(e)) from e

    if ref.kind == "channel_id":
        return ResolvedInput(kind="channel", id=ref.value)
    if ref.kind == "handle":
        return ResolvedInput(kind="channel", id=f"@{ref.value}")
    raise InputResolveError("Unsupported input")
