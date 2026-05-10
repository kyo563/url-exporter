from __future__ import annotations

import os
import sys
from dataclasses import dataclass

import yaml

from scripts.channel_resolver import ChannelUrlError, parse_channel_url
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


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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

    settings = config.get("settings", {})
    channels = [ChannelConfig(**c) for c in config.get("channels", [])]
    client = YouTubeClient(api_key=api_key)

    threshold = int(settings.get("shorts_duration_threshold_sec", 180))
    include_active_live = bool(settings.get("include_active_live", True))
    include_upcoming_live = bool(settings.get("include_upcoming_live", True))
    max_pages = settings.get("max_pages")
    max_items = settings.get("max_items")

    all_urls: list[str] = []
    debug_rows: list[dict] = []
    seen_ids: set[str] = set()

    for channel in channels:
        info(f"Resolve channel: {channel.url}")
        try:
            ref = parse_channel_url(channel.url)
        except ChannelUrlError as e:
            error(str(e))
            debug_rows.append(
                {
                    "channel_name": channel.name,
                    "channel_url": channel.url,
                    "video_id": "",
                    "url": "",
                    "raw_duration": "",
                    "duration_sec": "",
                    "live_broadcast_content": "",
                    "included": False,
                    "excluded_reason": "unsupported_url",
                }
            )
            continue

        try:
            if ref.kind == "channel_id":
                channel_data = client.get_channel_content_details(channel_id=ref.value)
            else:
                channel_data = client.get_channel_content_details(handle=ref.value)
        except YouTubeApiError as e:
            error(f"Failed to resolve channel {channel.url}: {e}")
            debug_rows.append({"channel_name": channel.name, "channel_url": channel.url, "video_id": "", "url": "", "raw_duration": "", "duration_sec": "", "live_broadcast_content": "", "included": False, "excluded_reason": "channel_not_found"})
            continue

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
        video_ids: list[str] = []
        while True:
            page += 1
            info(f"Fetch uploads playlist items: page={page}")
            try:
                page_data = client.get_playlist_items(uploads_id, page_token=page_token)
            except YouTubeApiError as e:
                error(f"Failed playlist fetch for {channel.url}: {e}")
                break

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

        info(f"Total video IDs fetched: {len(video_ids)}")

        for idx, batch in enumerate(chunked(video_ids, 50), start=1):
            info(f"Fetch videos details: batch={idx} size={len(batch)}")
            try:
                detail_data = client.get_videos_details(batch)
            except YouTubeApiError as e:
                error(f"Failed video details fetch for batch={idx}: {e}")
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
