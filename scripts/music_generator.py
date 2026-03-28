"""
Music generation and retrieval helpers for Astro Shorts.

Priority order:
1. Suno-compatible unofficial API (self-hosted, optional)
2. Mubert API (optional)
3. Pixabay music search/download
4. Local fallback from assets/audio/
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Iterable

import requests


ROOT_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT_DIR / "assets" / "audio"
GENERATED_DIR = AUDIO_DIR / "generated"

SUNO_API_URL = os.environ.get("SUNO_API_URL", "").rstrip("/")
SUNO_COOKIE = os.environ.get("SUNO_COOKIE", "")
MUBERT_API_KEY = os.environ.get("MUBERT_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")

DEFAULT_MOOD = "cinematic"
USER_AGENT = "astro-shorts-v2/1.0"


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return text or "cinematic"


def build_music_prompt(mood: str) -> str:
    normalized = mood.strip() or DEFAULT_MOOD
    return f"cinematic space ambient, no vocals, {normalized}, epic orchestral"


def cache_key(mood: str, duration_seconds: float) -> tuple[str, Path]:
    normalized = slugify(mood)
    seed = f"{normalized}|{round(duration_seconds, 2)}"
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()[:10]
    filename = f"{normalized}_{digest}.mp3"
    return normalized, GENERATED_DIR / filename


def request_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def write_audio_file(path: Path, content: bytes) -> str | None:
    if not content:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return str(path)


def download_binary(url: str, destination: Path, session: requests.Session, timeout: int = 180) -> str | None:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return write_audio_file(destination, response.content)


def gather_local_audio_files() -> list[Path]:
    if not AUDIO_DIR.exists():
        return []
    files: list[Path] = []
    for item in AUDIO_DIR.iterdir():
        if item.is_file() and item.suffix.lower() in {".mp3", ".wav", ".ogg", ".m4a"}:
            files.append(item)
    generated_files = [item for item in GENERATED_DIR.glob("*.mp3") if item.is_file()]
    return files + generated_files


def choose_local_fallback(mood: str, destination: Path) -> str | None:
    files = gather_local_audio_files()
    if not files:
        return None

    normalized = slugify(mood)
    ranked = [item for item in files if normalized in item.stem.lower()]
    candidates = ranked or files
    ordered = sorted(candidates)
    pick = ordered[hash(normalized) % len(ordered)]

    if pick.resolve() == destination.resolve():
        return str(pick)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pick.read_bytes())
    return str(destination)


def suno_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    if SUNO_COOKIE:
        headers["Cookie"] = SUNO_COOKIE
    return headers


def try_suno(mood: str, duration_seconds: float, destination: Path, session: requests.Session) -> str | None:
    if not SUNO_API_URL:
        return None

    prompt = build_music_prompt(mood)
    payload = {
        "prompt": prompt,
        "tags": f"instrumental, cinematic, space, {mood}",
        "title": f"Astro Shorts {mood.title()}",
        "make_instrumental": True,
        "wait_audio": False,
    }

    try:
        response = session.post(
            f"{SUNO_API_URL}/api/custom_generate",
            json=payload,
            headers=suno_headers(),
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            items = data.get("clips") or data.get("data") or data.get("songs") or []
        else:
            items = data
        if not items:
            return None

        ids = ",".join(str(item.get("id")) for item in items if item.get("id"))
        if not ids:
            return None

        deadline = time.time() + 210
        while time.time() < deadline:
            poll = session.get(
                f"{SUNO_API_URL}/api/get",
                params={"ids": ids},
                headers=suno_headers(),
                timeout=60,
            )
            poll.raise_for_status()
            status_data = poll.json()
            if isinstance(status_data, dict):
                clips = status_data.get("clips") or status_data.get("data") or []
            else:
                clips = status_data
            for clip in clips:
                audio_url = clip.get("audio_url")
                if audio_url:
                    return download_binary(audio_url, destination, session)
            time.sleep(6)
    except Exception as exc:
        print(f"Warning: Suno provider failed: {exc}")
    return None


def try_mubert(mood: str, duration_seconds: float, destination: Path, session: requests.Session) -> str | None:
    if not MUBERT_API_KEY:
        return None

    rounded_duration = max(15, min(30, int(round(duration_seconds))))
    payload_variants = [
        (
            "https://music-api.mubert.com/api/v3/public/tracks",
            {
                "duration": rounded_duration,
                "prompt": build_music_prompt(mood),
                "playlist": mood,
                "format": "mp3",
                "mode": "track",
            },
            {"Authorization": f"Bearer {MUBERT_API_KEY}"},
        ),
        (
            "https://api.mubert.com/v2/generate/track",
            {
                "duration": rounded_duration,
                "mood": mood,
                "tags": [mood, "cinematic", "space", "instrumental"],
                "format": "mp3",
            },
            {"Authorization": f"Bearer {MUBERT_API_KEY}"},
        ),
    ]

    for url, payload, headers in payload_variants:
        try:
            response = session.post(url, json=payload, headers=headers, timeout=120)
            if response.status_code >= 400:
                continue
            data = response.json()
            audio_url = extract_audio_url(data)
            if audio_url:
                return download_binary(audio_url, destination, session)
        except Exception as exc:
            print(f"Warning: Mubert provider failed at {url}: {exc}")
    return None


def extract_audio_url(value) -> str | None:
    if isinstance(value, str):
        if value.startswith("http") and any(ext in value for ext in (".mp3", ".wav", ".m4a", ".ogg")):
            return value
        return None
    if isinstance(value, list):
        for item in value:
            found = extract_audio_url(item)
            if found:
                return found
        return None
    if isinstance(value, dict):
        for key in ("audio_url", "audioUrl", "url", "download_url", "downloadUrl", "track_url", "trackUrl"):
            found = value.get(key)
            if isinstance(found, str) and found.startswith("http"):
                return found
        for child in value.values():
            found = extract_audio_url(child)
            if found:
                return found
    return None


def pixabay_headers() -> dict[str, str]:
    if not PIXABAY_API_KEY:
        return {}
    return {"X-API-Key": PIXABAY_API_KEY}


def pixabay_search_candidates(mood: str, session: requests.Session) -> Iterable[str]:
    queries = [
        f"{mood} space ambient instrumental",
        f"{mood} cinematic instrumental",
        mood,
    ]
    for query in queries:
        encoded = requests.utils.quote(query)
        yield f"https://pixabay.com/music/search/{encoded}/"


def try_pixabay(mood: str, duration_seconds: float, destination: Path, session: requests.Session) -> str | None:
    mp3_pattern = re.compile(r'https://cdn\.pixabay\.com/download/audio/[^"\']+?\.mp3')

    for search_url in pixabay_search_candidates(mood, session):
        try:
            response = session.get(search_url, headers=pixabay_headers(), timeout=60)
            if response.status_code >= 400:
                continue
            matches = mp3_pattern.findall(response.text)
            if matches:
                unique_matches = list(dict.fromkeys(matches))
                selected = unique_matches[min(len(unique_matches) - 1, abs(hash(mood)) % min(len(unique_matches), 3))]
                return download_binary(selected, destination, session)
        except Exception as exc:
            print(f"Warning: Pixabay provider failed for {search_url}: {exc}")
    return None


def get_music_for_mood(mood: str, duration_seconds: float) -> str | None:
    """Returns path to a .mp3 file, or None if all sources fail."""
    normalized_mood, destination = cache_key(mood or DEFAULT_MOOD, duration_seconds)
    if destination.exists():
        return str(destination)

    session = request_session()

    providers = (
        ("Suno", lambda: try_suno(normalized_mood, duration_seconds, destination, session)),
        ("Mubert", lambda: try_mubert(normalized_mood, duration_seconds, destination, session)),
        ("Pixabay", lambda: try_pixabay(normalized_mood, duration_seconds, destination, session)),
        ("Local fallback", lambda: choose_local_fallback(normalized_mood, destination)),
    )

    for label, provider in providers:
        path = provider()
        if path and Path(path).exists():
            print(f"Music source: {label} -> {path}")
            return path

    return None


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Fetch or generate music for a mood.")
    parser.add_argument("mood", help="Topic mood, such as epic or unsettling")
    parser.add_argument("--duration", type=float, default=30.0, help="Track length target in seconds")
    args = parser.parse_args()

    path = get_music_for_mood(args.mood, args.duration)
    if path:
        print(path)
        raise SystemExit(0)
    print("No music source succeeded.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
