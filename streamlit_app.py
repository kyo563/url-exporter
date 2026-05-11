from __future__ import annotations

import csv
import io
import os

import streamlit as st

from scripts.channel_resolver import ChannelUrlError, parse_channel_url
from scripts.duration import parse_iso8601_duration_to_seconds
from scripts.export_urls import chunked, is_fatal_api_error
from scripts.filters import should_include_video
from scripts.youtube_client import YouTubeApiError, YouTubeClient


def get_api_key() -> str | None:
    try:
        key = st.secrets.get("YOUTUBE_API_KEY")
        if key:
            return str(key)
    except Exception:
        pass
    return os.getenv("YOUTUBE_API_KEY")


def build_txt(urls: list[str]) -> str:
    return "\n".join(urls)


def _write_csv(rows: list[dict], fieldnames: list[str]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def build_url_csv(urls: list[str]) -> str:
    return _write_csv([{"url": u} for u in urls], ["url"])


def build_debug_csv(rows: list[dict]) -> str:
    fields = [
        "channel_name",
        "channel_url",
        "video_id",
        "url",
        "raw_duration",
        "duration_sec",
        "live_broadcast_content",
        "included",
        "excluded_reason",
    ]
    return _write_csv(rows, fields)


def fetch_urls_for_channel(
    *,
    api_key: str,
    channel_url: str,
    channel_name: str,
    exclude_shorts: bool,
    shorts_duration_threshold_sec: int,
    include_active_live: bool,
    include_upcoming_live: bool,
    max_pages: int,
    max_items: int,
) -> tuple[list[str], list[dict], dict]:
    client = YouTubeClient(api_key=api_key)
    debug_rows: list[dict] = []
    seen_ids: set[str] = set()
    urls: list[str] = []

    ref = parse_channel_url(channel_url)
    if ref.kind == "channel_id":
        channel_data = client.get_channel_content_details(channel_id=ref.value)
    else:
        channel_data = client.get_channel_content_details(handle=ref.value)

    items = channel_data.get("items", [])
    if not items:
        raise RuntimeError("channel_not_found")

    uploads_id = items[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not uploads_id:
        raise RuntimeError("uploads_playlist_not_found")

    page = 0
    page_token = None
    video_ids: list[str] = []
    while True:
        page += 1
        page_data = client.get_playlist_items(uploads_id, page_token=page_token)

        for it in page_data.get("items", []):
            vid = it.get("contentDetails", {}).get("videoId")
            if vid:
                video_ids.append(vid)
                if max_items > 0 and len(video_ids) >= max_items:
                    break

        if max_items > 0 and len(video_ids) >= max_items:
            break
        if max_pages > 0 and page >= max_pages:
            break

        page_token = page_data.get("nextPageToken")
        if not page_token:
            break

    for batch in chunked(video_ids, 50):
        detail_data = client.get_videos_details(batch)
        detail_map = {it.get("id"): it for it in detail_data.get("items", [])}

        for vid in batch:
            item = detail_map.get(vid)
            url = f"https://www.youtube.com/watch?v={vid}"
            if not item:
                debug_rows.append({"channel_name": channel_name, "channel_url": channel_url, "video_id": vid, "url": url, "raw_duration": "", "duration_sec": "", "live_broadcast_content": "", "included": False, "excluded_reason": "api_video_not_found"})
                continue

            raw_duration = item.get("contentDetails", {}).get("duration")
            duration_sec = parse_iso8601_duration_to_seconds(raw_duration) if raw_duration else None
            live_state = item.get("snippet", {}).get("liveBroadcastContent", "none")

            included, reason = should_include_video(
                duration_sec=duration_sec,
                live_broadcast_content=live_state,
                shorts_duration_threshold_sec=shorts_duration_threshold_sec,
                include_active_live=include_active_live,
                include_upcoming_live=include_upcoming_live,
                exclude_shorts=exclude_shorts,
            )

            if included and vid not in seen_ids:
                seen_ids.add(vid)
                urls.append(url)

            debug_rows.append(
                {
                    "channel_name": channel_name,
                    "channel_url": channel_url,
                    "video_id": vid,
                    "url": url,
                    "raw_duration": raw_duration or "",
                    "duration_sec": duration_sec if duration_sec is not None else "",
                    "live_broadcast_content": live_state,
                    "included": included,
                    "excluded_reason": reason,
                }
            )

    stats = {
        "fetched_video_ids": len(video_ids),
        "output_urls": len(urls),
        "excluded_count": len([r for r in debug_rows if not r.get("included")]),
    }
    return urls, debug_rows, stats


st.set_page_config(page_title="YouTube URL Exporter")

channel_url = st.text_input("YouTubeチャンネルURL", placeholder="https://www.youtube.com/@handle")

channel_name = "streamlit_input"
exclude_shorts = True
shorts_threshold = 180
include_active_live = False
include_upcoming_live = False
max_pages = 0
max_items = 0

if st.button("URL一覧を生成"):
    api_key = get_api_key()
    if not api_key:
        st.error("YOUTUBE_API_KEY が見つかりません。Streamlit Cloudの Secrets に `YOUTUBE_API_KEY = \"YOUR_API_KEY\"` を設定してください。")
        st.stop()

    if not channel_url.strip():
        st.error("YouTubeチャンネルURLを入力してください。")
        st.stop()

    try:
        urls, debug_rows, stats = fetch_urls_for_channel(
            api_key=api_key,
            channel_url=channel_url.strip(),
            channel_name=channel_name,
            exclude_shorts=exclude_shorts,
            shorts_duration_threshold_sec=int(shorts_threshold),
            include_active_live=include_active_live,
            include_upcoming_live=include_upcoming_live,
            max_pages=int(max_pages),
            max_items=int(max_items),
        )
    except ChannelUrlError as e:
        st.error(f"未対応のURL形式です: {e}")
        st.stop()
    except YouTubeApiError as e:
        if is_fatal_api_error(e):
            st.error("YouTube APIキーまたはAPI利用設定に問題があります。キーやYouTube Data API有効化状態を確認してください。")
        else:
            st.error("YouTube API呼び出し中にエラーが発生しました。安全のため部分結果は表示しません。時間をおいて再実行してください。")
        st.stop()
    except Exception as e:
        st.error(f"処理を完了できませんでした: {e}")
        st.stop()

    txt_content = build_txt(urls)
    url_csv_content = build_url_csv(urls)
    debug_csv_content = build_debug_csv(debug_rows)

    st.success("URL一覧を生成しました。")
    st.write(f"取得対象動画ID数: {stats['fetched_video_ids']}")
    st.write(f"出力URL数: {stats['output_urls']}")
    st.write(f"除外件数: {stats['excluded_count']}")

    st.text_area("NotebookLM貼り付け用URL一覧", value=txt_content, height=260)

    st.download_button("TXTダウンロード", data=txt_content, file_name="notebooklm_urls.txt", mime="text/plain")
    st.download_button("CSVダウンロード", data=url_csv_content, file_name="notebooklm_urls.csv", mime="text/csv")
    st.download_button("debug CSVダウンロード", data=debug_csv_content, file_name="notebooklm_urls_debug.csv", mime="text/csv")

    with st.expander("除外理由を確認"):
        st.dataframe(debug_rows)
