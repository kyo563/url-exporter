from __future__ import annotations

import csv
from pathlib import Path


def write_txt(path: str, urls: list[str]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(urls), encoding="utf-8")


def write_url_csv(path: str, urls: list[str]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["url"])
        for url in urls:
            writer.writerow([url])


def write_debug_csv(path: str, rows: list[dict]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
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
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
