"""
Background video fetcher.

Uses Pixabay video search as the default free source for looping background clips.
Downloaded clips are cached locally for reuse.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import requests


ROOT_DIR = Path(__file__).resolve().parent.parent
BACKGROUND_VIDEO_DIR = ROOT_DIR / "assets" / "videos" / "backgrounds"
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")

STYLE_DEFAULT_QUERIES = {
    "character_explainer": ["minecraft parkour", "gaming background", "parkour game"],
    "educational_voiceless": ["space background", "abstract science", "cosmos"],
    "planet_character": ["space stars", "nebula background", "galaxy background"],
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "background"


def cache_path(style_id: str, query: str) -> Path:
    key = f"{style_id}:{query}".encode("utf-8")
    digest = hashlib.md5(key).hexdigest()[:10]
    return BACKGROUND_VIDEO_DIR / f"{slugify(style_id)}_{slugify(query)}_{digest}.mp4"


def choose_video_url(hit: dict) -> str | None:
    videos = hit.get("videos", {})
    for size_key in ("medium", "small", "tiny", "large"):
        candidate = videos.get(size_key, {})
        url = candidate.get("url")
        if url:
            return url
    return None


def query_pixabay(query: str) -> dict | None:
    if not PIXABAY_API_KEY:
        return None
    response = requests.get(
        "https://pixabay.com/api/videos/",
        params={
            "key": PIXABAY_API_KEY,
            "q": query,
            "video_type": "all",
            "safesearch": "true",
            "order": "popular",
            "per_page": 10,
        },
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def download_video(url: str, destination: Path) -> str | None:
    response = requests.get(url, timeout=180, stream=True)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as file_obj:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                file_obj.write(chunk)
    return str(destination)


def local_fallback(style_id: str) -> str | None:
    if not BACKGROUND_VIDEO_DIR.exists():
        return None
    candidates = sorted(BACKGROUND_VIDEO_DIR.glob(f"{slugify(style_id)}_*.mp4"))
    if candidates:
        return str(candidates[0])
    any_candidates = sorted(BACKGROUND_VIDEO_DIR.glob("*.mp4"))
    if any_candidates:
        return str(any_candidates[0])
    return None


def get_background_video(style_id: str, topic: str = "", query: str | None = None) -> str | None:
    queries = [query] if query else []
    queries.extend(STYLE_DEFAULT_QUERIES.get(style_id, []))
    if topic:
        queries.append(topic)

    for raw_query in [q for q in queries if q]:
        destination = cache_path(style_id, raw_query)
        if destination.exists():
            return str(destination)
        try:
            payload = query_pixabay(raw_query)
        except Exception:
            payload = None
        if not payload:
            continue
        for hit in payload.get("hits", []):
            url = choose_video_url(hit)
            if not url:
                continue
            try:
                return download_video(url, destination)
            except Exception:
                continue

    return local_fallback(style_id)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch a background video for a style.")
    parser.add_argument("style_id")
    parser.add_argument("--topic", default="")
    parser.add_argument("--query", default=None)
    args = parser.parse_args()
    path = get_background_video(args.style_id, topic=args.topic, query=args.query)
    if path:
        print(path)
