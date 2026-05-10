from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


class ChannelUrlError(ValueError):
    pass


@dataclass(frozen=True)
class ChannelRef:
    kind: str
    value: str


def parse_channel_url(url: str) -> ChannelRef:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = parsed.path.strip("/")

    if host not in {"youtube.com", "www.youtube.com"}:
        raise ChannelUrlError(f"Unsupported domain: {host}")

    parts = path.split("/") if path else []
    if len(parts) >= 2 and parts[0] == "channel" and parts[1].startswith("UC"):
        return ChannelRef(kind="channel_id", value=parts[1])

    if parts and parts[0].startswith("@") and len(parts[0]) > 1:
        return ChannelRef(kind="handle", value=parts[0][1:])

    if parts and parts[0] in {"c", "user"}:
        raise ChannelUrlError(
            "Unsupported URL format. Use /@handle or /channel/UC... URLs."
        )

    raise ChannelUrlError(
        "Unsupported channel URL. Use https://www.youtube.com/@handle or https://www.youtube.com/channel/UC..."
    )
