from __future__ import annotations

from dataclasses import dataclass

import requests

BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, endpoint: str = "", response_text: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint
        self.response_text = response_text


@dataclass
class YouTubeClient:
    api_key: str
    timeout: int = 30

    def _request(self, endpoint: str, params: dict) -> dict:
        url = f"{BASE_URL}/{endpoint}"
        full_params = {**params, "key": self.api_key}
        try:
            resp = requests.get(url, params=full_params, timeout=self.timeout)
        except requests.RequestException as e:
            raise YouTubeApiError(
                f"YouTube API request failed: endpoint={endpoint} reason={e}",
                endpoint=endpoint,
                response_text=str(e),
            ) from e

        if resp.status_code >= 400:
            raise YouTubeApiError(
                f"YouTube API error: status={resp.status_code} endpoint={endpoint}",
                status_code=resp.status_code,
                endpoint=endpoint,
                response_text=resp.text,
            )
        return resp.json()

    def get_channel_content_details(self, *, channel_id: str | None = None, handle: str | None = None) -> dict:
        params = {
            "part": "contentDetails",
            "fields": "items(id,contentDetails/relatedPlaylists/uploads)",
            "maxResults": 1,
        }
        if channel_id:
            params["id"] = channel_id
        elif handle:
            params["forHandle"] = handle
        else:
            raise ValueError("channel_id or handle is required")
        return self._request("channels", params)

    def get_playlist_items(self, playlist_id: str, page_token: str | None = None) -> dict:
        params = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
            "fields": "nextPageToken,items/contentDetails/videoId",
        }
        if page_token:
            params["pageToken"] = page_token
        return self._request("playlistItems", params)


    def list_playlist_video_urls(self, playlist_id: str) -> list[str]:
        urls: list[str] = []
        page_token: str | None = None
        while True:
            data = self.get_playlist_items(playlist_id, page_token=page_token)
            for it in data.get("items", []):
                video_id = it.get("contentDetails", {}).get("videoId")
                if video_id:
                    urls.append(f"https://www.youtube.com/watch?v={video_id}")
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return urls

    def get_videos_details(self, video_ids: list[str]) -> dict:
        params = {
            "part": "contentDetails,snippet",
            "id": ",".join(video_ids),
            "maxResults": 50,
            "fields": "items(id,contentDetails/duration,snippet/liveBroadcastContent)",
        }
        return self._request("videos", params)
