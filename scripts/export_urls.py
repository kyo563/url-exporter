from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import yaml

from scripts.input_resolver import InputResolveError, resolve_input
from scripts.duration import parse_iso8601_duration_to_seconds
from scripts.filters import should_include_video
from scripts.writers import write_debug_csv, write_txt, write_url_csv
from scripts.youtube_client import YouTubeApiError, YouTubeClient


@dataclass
class ChannelConfig:
    name: str
    url: str


def info(message: str) -> None:
    print(f"[INFO] {message}")


def error(message: str) -> None:
    print(f"[ERROR] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def is_fatal_api_error(e: YouTubeApiError) -> bool:
    text = (e.response_text or "").lower()
    if e.status_code in {401, 403}:
        return True
    fatal_keywords = [
        "invalid api key",
        "api key not valid",
        "accessnotconfigured",
        "youtube data api",
        "quotaexceeded",
        "dailylimitexceeded",
    ]
    return any(k in text for k in fatal_keywords)


def parse_channels(config: dict) -> tuple[list[ChannelConfig], str | None]:
    raw_channels = config.get("channels")
    if raw_channels is None:
        return [], "Config error: 'channels' is required."
    if not isinstance(raw_channels, list) or len(raw_channels) == 0:
        return [], "Config error: 'channels' must be a non-empty list."

    channels: list[ChannelConfig] = []
    for idx, c in enumerate(raw_channels, start=1):
        if not isinstance(c, dict):
            return [], f"Config error: channels[{idx}] must be an object with 'name' and 'url'."
        name = c.get("name")
        url = c.get("url")
        if not name:
            return [], f"Config error: channels[{idx}].name is required."
        if not url:
            return [], f"Config error: channels[{idx}].url is required."
        channels.append(ChannelConfig(name=name, url=url))
    return channels, None


def should_abort_before_write(had_api_error: bool, included_count: int, fail_on_partial_api_error: bool) -> bool:
    if had_api_error and included_count == 0:
        return True
    return had_api_error and fail_on_partial_api_error


def get_fail_on_partial_api_error(settings: dict) -> bool:
    return bool(settings.get("fail_on_partial_api_error", True))


def main() -> int:
    info("Start export")
    config_path = "config/channels.yml"
    info(f"Load config: {config_path}")

    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        error("YOUTUBE_API_KEY is not set. Please set environment variable YOUTUBE_API_KEY.")
        return 1

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        error(f"Config file not found: {config_path}")
        return 1

    channels, config_error = parse_channels(config)
    if config_error:
        error(config_error)
        return 1

    settings = config.get("settings", {})
    client = YouTubeClient(api_key=api_key)

    threshold = int(settings.get("shorts_duration_threshold_sec", 180))
    exclude_shorts = bool(settings.get("exclude_shorts", True))
    include_active_live = bool(settings.get("include_active_live", True))
    include_upcoming_live = bool(settings.get("include_upcoming_live", True))
    fail_on_partial_api_error = get_fail_on_partial_api_error(settings)
    max_pages = settings.get("max_pages")
    max_items = settings.get("max_items")

    all_urls: list[str] = []
    debug_rows: list[dict] = []
    seen_ids: set[str] = set()
    had_api_error = False

    for channel in channels:
        info(f"Resolve channel: {channel.url}")
        try:
            resolved = resolve_input(channel.url)
        except InputResolveError as e:
            error(str(e))
            debug_rows.append({"channel_name": channel.name, "channel_url": channel.url, "video_id": "", "url": "", "raw_duration": "", "duration_sec": "", "live_broadcast_content": "", "included": False, "excluded_reason": "unsupported_url"})
            continue

        video_ids: list[str] = []
        try:
            if resolved.kind == "playlist":
                page_token = None
                page = 0
                while True:
                    page += 1
                    info(f"Fetch playlist items: page={page}")
                    page_data = client.get_playlist_items(resolved.id, page_token=page_token)
                    for it in page_data.get("items", []):
                        vid = it.get("contentDetails", {}).get("videoId")
                        if vid:
                            video_ids.append(vid)
                            if max_items is not None and len(video_ids) >= int(max_items):
                                break
                    if max_items is not None and len(video_ids) >= int(max_items):
                        break
                    if max_pages is not None and page >= int(max_pages):
                        break
                    page_token = page_data.get("nextPageToken")
                    if not page_token:
                        break
            else:
                if resolved.id.startswith("@"):
                    channel_data = client.get_channel_content_details(handle=resolved.id[1:])
                else:
                    channel_data = client.get_channel_content_details(channel_id=resolved.id)

                items = channel_data.get("items", [])
                if not items:
                    error(f"Channel not found: {channel.url}")
                    debug_rows.append({"channel_name": channel.name, "channel_url": channel.url, "video_id": "", "url": "", "raw_duration": "", "duration_sec": "", "live_broadcast_content": "", "included": False, "excluded_reason": "channel_not_found"})
                    continue

                uploads_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
                if not uploads_id:
                    error(f"Uploads playlist not found: {channel.url}")
                    continue

                page = 0
                page_token = None
                while True:
                    page += 1
                    info(f"Fetch uploads playlist items: page={page}")
                    page_data = client.get_playlist_items(uploads_id, page_token=page_token)
                    for it in page_data.get("items", []):
                        vid = it.get("contentDetails", {}).get("videoId")
                        if vid:
                            video_ids.append(vid)
                            if max_items is not None and len(video_ids) >= int(max_items):
                                break
                    if max_items is not None and len(video_ids) >= int(max_items):
                        break
                    if max_pages is not None and page >= int(max_pages):
                        break
                    page_token = page_data.get("nextPageToken")
                    if not page_token:
                        break
        except YouTubeApiError as e:
            error(f"Failed to fetch for {channel.url}: endpoint={e.endpoint} reason={e}")
            if is_fatal_api_error(e):
                error("Fatal API error detected. Stop entire process.")
                return 1
            had_api_error = True
            continue

        info(f"Total video IDs fetched: {len(video_ids)}")

        for idx, batch in enumerate(chunked(video_ids, 50), start=1):
            info(f"Fetch videos details: batch={idx} size={len(batch)}")
            try:
                detail_data = client.get_videos_details(batch)
            except YouTubeApiError as e:
                error(f"Failed video details fetch for batch={idx}: endpoint={e.endpoint} reason={e}")
                if is_fatal_api_error(e):
                    error("Fatal API error detected. Stop entire process.")
                    return 1
                had_api_error = True
                for vid in batch:
                    debug_rows.append({"channel_name": channel.name, "channel_url": channel.url, "video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}", "raw_duration": "", "duration_sec": "", "live_broadcast_content": "", "included": False, "excluded_reason": "api_video_not_found"})
                continue

            detail_map = {it.get("id"): it for it in detail_data.get("items", [])}
            for vid in batch:
                item = detail_map.get(vid)
                url = f"https://www.youtube.com/watch?v={vid}"
                if not item:
                    debug_rows.append({"channel_name": channel.name, "channel_url": channel.url, "video_id": vid, "url": url, "raw_duration": "", "duration_sec": "", "live_broadcast_content": "", "included": False, "excluded_reason": "api_video_not_found"})
                    continue

                raw_duration = item.get("contentDetails", {}).get("duration")
                duration_sec = parse_iso8601_duration_to_seconds(raw_duration) if raw_duration else None
                live_state = item.get("snippet", {}).get("liveBroadcastContent", "none")

                included, reason = should_include_video(
                    duration_sec=duration_sec,
                    live_broadcast_content=live_state,
                    shorts_duration_threshold_sec=threshold,
                    include_active_live=include_active_live,
                    include_upcoming_live=include_upcoming_live,
                    exclude_shorts=exclude_shorts,
                )

                if included and vid not in seen_ids:
                    seen_ids.add(vid)
                    all_urls.append(url)

                debug_rows.append({
                    "channel_name": channel.name,
                    "channel_url": channel.url,
                    "video_id": vid,
                    "url": url,
                    "raw_duration": raw_duration or "",
                    "duration_sec": duration_sec if duration_sec is not None else "",
                    "live_broadcast_content": live_state,
                    "included": included,
                    "excluded_reason": reason,
                })

    included_count = len(all_urls)
    excluded_count = len([r for r in debug_rows if not r.get("included")])
    info(f"Included URLs: {included_count}")
    info(f"Excluded videos: {excluded_count}")

    if should_abort_before_write(
        had_api_error=had_api_error,
        included_count=included_count,
        fail_on_partial_api_error=fail_on_partial_api_error,
    ):
        if included_count == 0:
            error("Export failed: API error occurred and no URLs were collected.")
        else:
            error("Export aborted: API error occurred during export and fail_on_partial_api_error is enabled. Existing output files were not overwritten.")
        return 1
    if had_api_error and not fail_on_partial_api_error:
        warn("API error occurred, but fail_on_partial_api_error is disabled. Partial outputs will be written.")

    out_txt = settings.get("output_txt", "data/output/notebooklm_urls.txt")
    out_csv = settings.get("output_csv", "data/output/notebooklm_urls.csv")
    debug_csv = settings.get("debug_csv", "data/debug/notebooklm_urls_debug.csv")

    write_txt(out_txt, all_urls)
    info(f"Write TXT: {out_txt}")
    write_url_csv(out_csv, all_urls)
    info(f"Write CSV: {out_csv}")
    write_debug_csv(debug_csv, debug_rows)
    info(f"Write debug CSV: {debug_csv}")
    info("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
