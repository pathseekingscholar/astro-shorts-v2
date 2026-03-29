"""
Space image fetcher for Astro Shorts.

Fetches and caches real public-domain astronomy images for use as background plates.
Priority order:
1. NASA APOD
2. NASA Image Library
3. ESA Hubble archive
4. Hubble Legacy Archive
"""

from __future__ import annotations

import hashlib
import io
import os
import re
from pathlib import Path

import requests
from PIL import Image


ROOT_DIR = Path(__file__).resolve().parent.parent
BACKGROUNDS_DIR = ROOT_DIR / "assets" / "backgrounds"
NASA_API_KEY = os.environ.get("NASA_API_KEY", "")

PLANET_NAMES = {
    "earth",
    "mars",
    "jupiter",
    "saturn",
    "sun",
    "moon",
    "neptune",
    "venus",
    "mercury",
    "uranus",
    "black_hole",
    "neutron_star",
}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "space"


def infer_topic_keyword(script_data: dict) -> str:
    idea = script_data.get("idea", {})
    render_plan = script_data.get("render_plan") or script_data.get("renderPlan") or {}
    metadata = script_data.get("metadata") or {}

    explicit = (
        render_plan.get("background_query")
        or render_plan.get("backgroundQuery")
        or metadata.get("background_search")
        or metadata.get("backgroundSearch")
    )
    if explicit:
        return str(explicit)

    topic = str(idea.get("topic", "")).lower()
    timeline = script_data.get("timeline", [])
    planet_names = [
        str(layer.get("name", ""))
        for scene in timeline
        for layer in scene.get("layers", [])
        if layer.get("type") == "planet"
    ]

    if "black hole" in topic or "black_hole" in topic:
        return "black hole"
    if any(word in topic for word in ("galaxy", "milky way", "universe", "nebula")):
        return "galaxy nebula"
    if any(word in topic for word in ("dark matter", "dark energy")):
        return "deep space nebula"
    if any(word in topic for word in ("travel", "distance", "light-year", "voyager")):
        return "galaxy stars"

    for name in planet_names:
        if name in PLANET_NAMES and name not in {"black_hole", "neutron_star"}:
            return f"planet {name.replace('_', ' ')}"

    return "space nebula"


def background_cache_path(keyword: str) -> Path:
    normalized = slugify(keyword)
    digest = hashlib.md5(keyword.encode("utf-8")).hexdigest()[:10]
    return BACKGROUNDS_DIR / f"{normalized}_{digest}.jpg"


def fetch_image_bytes(url: str, session: requests.Session, timeout: int = 90) -> bytes | None:
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception:
        return None


def select_best_apod(items: list[dict], keyword: str) -> dict | None:
    query_terms = [term for term in re.split(r"\W+", keyword.lower()) if term]
    best_item = None
    best_score = -1
    for item in items:
        if item.get("media_type") != "image":
            continue
        haystack = " ".join(str(item.get(field, "")).lower() for field in ("title", "explanation", "copyright"))
        score = sum(term in haystack for term in query_terms)
        if score > best_score:
            best_item = item
            best_score = score
    return best_item


def try_nasa_apod(keyword: str, session: requests.Session) -> bytes | None:
    if not NASA_API_KEY:
        return None
    try:
        response = session.get(
            "https://api.nasa.gov/planetary/apod",
            params={"api_key": NASA_API_KEY, "count": 5},
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            return None
        picked = select_best_apod(data, keyword)
        if not picked:
            return None
        image_url = picked.get("hdurl") or picked.get("url")
        if not image_url:
            return None
        return fetch_image_bytes(image_url, session)
    except Exception:
        return None


def extract_nasa_library_url(item: dict, session: requests.Session) -> str | None:
    for link in item.get("links") or []:
        href = link.get("href")
        if isinstance(href, str) and href.startswith("http"):
            return href

    data = item.get("data") or []
    if not data:
        return None
    nasa_id = data[0].get("nasa_id")
    if not nasa_id:
        return None

    try:
        response = session.get(f"https://images-api.nasa.gov/asset/{nasa_id}", timeout=45)
        response.raise_for_status()
        items = response.json().get("collection", {}).get("items", [])
        for asset in items:
            href = asset.get("href")
            if isinstance(href, str) and href.lower().endswith((".jpg", ".jpeg", ".png")):
                return href
    except Exception:
        return None
    return None


def try_nasa_library(keyword: str, session: requests.Session) -> bytes | None:
    try:
        response = session.get(
            "https://images-api.nasa.gov/search",
            params={"q": keyword, "media_type": "image", "page": 1},
            timeout=45,
        )
        response.raise_for_status()
        items = response.json().get("collection", {}).get("items", [])
        for item in items[:8]:
            image_url = extract_nasa_library_url(item, session)
            if image_url:
                image_bytes = fetch_image_bytes(image_url, session)
                if image_bytes:
                    return image_bytes
    except Exception:
        return None
    return None


def hubble_category_for_keyword(keyword: str) -> str:
    text = keyword.lower()
    if "black hole" in text:
        return "black-holes"
    if "planet" in text or "solar" in text:
        return "solar-system"
    if "nebula" in text:
        return "nebulae"
    return "galaxies"


def try_esa_hubble(keyword: str, session: requests.Session) -> bytes | None:
    category = hubble_category_for_keyword(keyword)
    urls = [
        f"https://esahubble.org/images/archive/category/{category}/?format=json",
        f"https://esahubble.org/images/archive/category/{category}/",
    ]
    for url in urls:
        try:
            response = session.get(url, timeout=45)
            response.raise_for_status()
            if "json" in response.headers.get("content-type", ""):
                data = response.json()
                items = data if isinstance(data, list) else data.get("results", [])
                for item in items[:8]:
                    image_url = item.get("fullsize_url") or item.get("url")
                    if image_url:
                        image_bytes = fetch_image_bytes(image_url, session)
                        if image_bytes:
                            return image_bytes
            else:
                match = re.search(r'https://cdn\.spacetelescope\.org/archives/images/[^"\']+\.(jpg|jpeg|png)', response.text)
                if match:
                    image_bytes = fetch_image_bytes(match.group(0), session)
                    if image_bytes:
                        return image_bytes
        except Exception:
            continue
    return None


def try_hubble_legacy(session: requests.Session) -> bytes | None:
    try:
        response = session.get(
            "https://hla.stsci.edu/cgi-bin/fitscut.cgi",
            params={
                "ra": "10.684",
                "dec": "41.269",
                "size": "700",
                "format": "jpeg",
                "red": "DSS2 Red",
                "green": "DSS2 Blue",
                "blue": "DSS2 IR",
            },
            timeout=45,
        )
        if response.ok and response.content:
            return response.content
    except Exception:
        return None
    return None


def normalize_and_cache(image_bytes: bytes, destination: Path) -> str | None:
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, quality=92)
        return str(destination)
    except Exception:
        return None


def get_space_background(keyword: str) -> str | None:
    cache_path = background_cache_path(keyword)
    if cache_path.exists():
        return str(cache_path)

    session = requests.Session()
    session.headers.update({"User-Agent": "astro-shorts-v2/1.0"})

    for provider in (
        lambda: try_nasa_apod(keyword, session),
        lambda: try_nasa_library(keyword, session),
        lambda: try_esa_hubble(keyword, session),
        lambda: try_hubble_legacy(session),
    ):
        image_bytes = provider()
        if image_bytes:
            cached = normalize_and_cache(image_bytes, cache_path)
            if cached:
                return cached

    return None


def get_space_background_for_script(script_data: dict) -> str | None:
    keyword = infer_topic_keyword(script_data)
    return get_space_background(keyword)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch a real space background image.")
    parser.add_argument("keyword", nargs="?", default="space nebula")
    args = parser.parse_args()
    path = get_space_background(args.keyword)
    if path:
        print(path)
