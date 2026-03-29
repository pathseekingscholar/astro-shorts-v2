"""
Dark Cosmos renderer for Astro Shorts.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import random
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path

import moviepy.audio.fx.all as afx
import numpy as np
import requests
from moviepy.editor import AudioFileClip, VideoClip
from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageEnhance, ImageFilter, ImageFont

try:
    from music_generator import get_music_for_mood
except ImportError:
    from scripts.music_generator import get_music_for_mood


BASE_WIDTH = 1080
BASE_HEIGHT = 1920
BASE_FPS = 24
WIDTH = BASE_WIDTH
HEIGHT = BASE_HEIGHT
FPS = BASE_FPS
HOOK_DURATION = 2.5
TRANSITION_DURATION = 0.45
PREVIEW_MODE = False

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts_output"
OUTPUT_DIR = ROOT_DIR / "videos_output"
BACKGROUNDS_DIR = ROOT_DIR / "assets" / "backgrounds"
FONTS_DIR = ROOT_DIR / "assets" / "fonts"

WHITE = (255, 255, 255)
NUMBER_YELLOW = ImageColor.getrgb("#FFD700")
PLANET_CYAN = ImageColor.getrgb("#00FFFF")
PILL_DARK = (5, 8, 16, 160)

POSITIONS = {
    "center": (0.50, 0.52),
    "left": (0.25, 0.54),
    "right": (0.75, 0.54),
    "top": (0.50, 0.30),
    "bottom": (0.50, 0.72),
    "top_left": (0.25, 0.30),
    "top_right": (0.75, 0.30),
    "bottom_left": (0.25, 0.74),
    "bottom_right": (0.75, 0.74),
}

SIZES = {
    "tiny": 55,
    "small": 92,
    "medium": 150,
    "large": 220,
    "huge": 300,
}

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

TOPIC_THEMES = {
    "black_hole": {
        "accent": ImageColor.getrgb("#B03060"),
        "accent_secondary": ImageColor.getrgb("#7A1FA2"),
        "nebula": ImageColor.getrgb("#240914"),
        "nebula_secondary": ImageColor.getrgb("#32124B"),
        "star_tint": ImageColor.getrgb("#FF9AAE"),
        "planet_glow": ImageColor.getrgb("#FF7A45"),
    },
    "galaxy": {
        "accent": ImageColor.getrgb("#7A6BFF"),
        "accent_secondary": ImageColor.getrgb("#284C9B"),
        "nebula": ImageColor.getrgb("#071731"),
        "nebula_secondary": ImageColor.getrgb("#221251"),
        "star_tint": ImageColor.getrgb("#A9B6FF"),
        "planet_glow": ImageColor.getrgb("#8290FF"),
    },
    "quantum": {
        "accent": ImageColor.getrgb("#39FF9C"),
        "accent_secondary": ImageColor.getrgb("#0F5F58"),
        "nebula": ImageColor.getrgb("#021A1C"),
        "nebula_secondary": ImageColor.getrgb("#0B3A34"),
        "star_tint": ImageColor.getrgb("#7BFFD6"),
        "planet_glow": ImageColor.getrgb("#36E3AE"),
    },
    "solar": {
        "accent": ImageColor.getrgb("#FFB347"),
        "accent_secondary": ImageColor.getrgb("#A55311"),
        "nebula": ImageColor.getrgb("#241204"),
        "nebula_secondary": ImageColor.getrgb("#4A2107"),
        "star_tint": ImageColor.getrgb("#FFD09A"),
        "planet_glow": ImageColor.getrgb("#FFB55A"),
    },
    "mystery": {
        "accent": ImageColor.getrgb("#D633FF"),
        "accent_secondary": ImageColor.getrgb("#68004F"),
        "nebula": ImageColor.getrgb("#18000F"),
        "nebula_secondary": ImageColor.getrgb("#4A033A"),
        "star_tint": ImageColor.getrgb("#FFA6F9"),
        "planet_glow": ImageColor.getrgb("#F758D4"),
    },
    "travel": {
        "accent": ImageColor.getrgb("#8FB8FF"),
        "accent_secondary": ImageColor.getrgb("#34567A"),
        "nebula": ImageColor.getrgb("#08121E"),
        "nebula_secondary": ImageColor.getrgb("#20364F"),
        "star_tint": ImageColor.getrgb("#C8E1FF"),
        "planet_glow": ImageColor.getrgb("#9AC5FF"),
    },
}

TRANSITIONS = ("crossfade", "horizontal_wipe", "zoom_through")
THEME_SCENE_EFFECTS = {
    "black_hole": ["lens_pulse", "star_swirl"],
    "galaxy": ["star_swirl"],
    "quantum": ["glitch", "speed_lines"],
    "solar": ["lens_pulse"],
    "mystery": ["vignette_pulse", "chromatic_aberration"],
    "travel": ["speed_lines", "lens_pulse"],
}


def configure_render_mode(preview: bool = False) -> None:
    global PREVIEW_MODE, WIDTH, HEIGHT, FPS
    PREVIEW_MODE = preview
    if preview:
        WIDTH = 540
        HEIGHT = 960
        FPS = 12
    else:
        WIDTH = BASE_WIDTH
        HEIGHT = BASE_HEIGHT
        FPS = BASE_FPS


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def ease_out_back(value: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1
    t = clamp(value, 0.0, 1.0)
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_cubic(value: float) -> float:
    t = clamp(value, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(value: float) -> float:
    t = clamp(value, 0.0, 1.0)
    if t < 0.5:
        return 4 * t * t * t
    return 1 - ((-2 * t + 2) ** 3) / 2


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "space"


def get_font(size: int, *, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        FONTS_DIR / "Montserrat-ExtraBold.ttf",
        FONTS_DIR / "Montserrat-Bold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ]
    if not bold:
        candidates = [
            FONTS_DIR / "Montserrat-Regular.ttf",
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ]

    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue
    return ImageFont.load_default()


def infer_theme(script_data: dict) -> str:
    idea = script_data.get("idea", {})
    text = " ".join(
        str(value)
        for value in (
            idea.get("topic", ""),
            idea.get("title", ""),
            idea.get("hook", ""),
            idea.get("topic_family", ""),
        )
    ).lower()

    if any(term in text for term in ("black hole", "singularity", "event horizon")):
        return "black_hole"
    if any(term in text for term in ("quantum", "particle", "atom", "boson")):
        return "quantum"
    if any(term in text for term in ("dark matter", "dark energy", "mystery", "unknown")):
        return "mystery"
    if any(term in text for term in ("travel", "light speed", "voyager", "distance", "reach")):
        return "travel"
    if any(term in text for term in ("planet", "solar", "mars", "jupiter", "saturn", "venus", "sun", "earth")):
        return "solar"
    return "galaxy"


def infer_topic_keyword(script_data: dict) -> str:
    idea = script_data.get("idea", {})
    topic = str(idea.get("topic", "")).lower()
    timeline = script_data.get("timeline", [])
    planet_names = [
        layer.get("name", "")
        for scene in timeline
        for layer in scene.get("layers", [])
        if layer.get("type") == "planet"
    ]
    if "black hole" in topic or "black_hole" in topic:
        return "black hole"
    if any(word in topic for word in ("galaxy", "milky way", "universe")):
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
    api_key = os.environ.get("NASA_API_KEY", "")
    if not api_key:
        return None
    try:
        response = session.get(
            "https://api.nasa.gov/planetary/apod",
            params={"api_key": api_key, "count": 5},
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


def try_hubble_legacy(keyword: str, session: requests.Session) -> bytes | None:
    del keyword
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


def get_space_background(keyword: str) -> tuple[Image.Image | None, Path | None]:
    cache_path = background_cache_path(keyword)
    if cache_path.exists():
        try:
            return Image.open(cache_path).convert("RGB"), cache_path
        except Exception:
            cache_path.unlink(missing_ok=True)

    BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "astro-shorts-v2/1.0"})

    image_bytes = None
    for provider in (try_nasa_apod, try_nasa_library, try_esa_hubble, try_hubble_legacy):
        image_bytes = provider(keyword, session)
        if image_bytes:
            break

    if not image_bytes:
        return None, None

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image.save(cache_path, quality=92)
        return image, cache_path
    except Exception:
        return None, None


def cover_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    resized = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def build_base_background(topic_image: Image.Image | None, theme_key: str) -> Image.Image:
    theme = TOPIC_THEMES[theme_key]
    if topic_image is None:
        base = Image.new("RGB", (WIDTH, HEIGHT), theme["nebula"])
    else:
        base = cover_resize(topic_image, (WIDTH, HEIGHT))
        base = ImageEnhance.Brightness(base).enhance(0.30)
        base = ImageEnhance.Contrast(base).enhance(0.85)

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(HEIGHT):
        blend = y / max(HEIGHT - 1, 1)
        color = tuple(
            int(theme["nebula"][idx] * (1 - blend) + theme["nebula_secondary"][idx] * blend)
            for idx in range(3)
        )
        draw.line((0, y, WIDTH, y), fill=(*color, 86))

    vignette = Image.new("L", (WIDTH, HEIGHT), 0)
    vignette_draw = ImageDraw.Draw(vignette)
    cx = WIDTH // 2
    cy = HEIGHT // 2
    max_radius = int(max(WIDTH, HEIGHT) * 0.78)
    for radius in range(max_radius, 0, -30):
        alpha = int(150 * (1 - radius / max_radius))
        vignette_draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=alpha)

    background = Image.alpha_composite(base.convert("RGBA"), overlay)
    dark_mask = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    dark_mask.putalpha(vignette)
    background = Image.alpha_composite(background, dark_mask)
    return background


def add_color_wash(frame: Image.Image, theme_key: str, t: float) -> Image.Image:
    theme = TOPIC_THEMES[theme_key]
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    sweep = 0.5 + 0.5 * math.sin(t * 0.45)
    top_alpha = int(34 + 24 * sweep)
    mid_alpha = int(26 + 18 * (1 - sweep))
    bottom_alpha = int(42 + 22 * (1 - sweep))
    draw.ellipse((-WIDTH * 0.22, -HEIGHT * 0.16, WIDTH * 0.68, HEIGHT * 0.46), fill=(*theme["accent"], top_alpha))
    draw.ellipse((WIDTH * 0.08, HEIGHT * 0.12, WIDTH * 0.92, HEIGHT * 0.72), fill=(*theme["star_tint"], mid_alpha))
    draw.ellipse((WIDTH * 0.28, HEIGHT * 0.42, WIDTH * 1.08, HEIGHT * 1.04), fill=(*theme["accent_secondary"], bottom_alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(84 if PREVIEW_MODE else 120))
    return Image.alpha_composite(frame.convert("RGBA"), overlay)


def build_particle_system(theme_key: str, keyword: str, total_duration: float) -> dict:
    rng = random.Random(hashlib.md5(f"{theme_key}:{keyword}".encode("utf-8")).hexdigest())
    theme = TOPIC_THEMES[theme_key]
    stars = []
    layer_counts = (80, 50, 28) if PREVIEW_MODE else (150, 95, 55)
    for depth, count in enumerate(layer_counts, start=1):
        layer = []
        for _ in range(count):
            layer.append(
                {
                    "x": rng.uniform(0, WIDTH),
                    "y": rng.uniform(0, HEIGHT),
                    "size": rng.uniform(0.8, 1.8 + depth * 0.5),
                    "speed_x": rng.uniform(-5, 5) * depth,
                    "speed_y": rng.uniform(-8, -2) * depth,
                    "alpha": rng.randint(80, 225),
                }
            )
        stars.append(layer)

    blobs = []
    blob_count = 2 if PREVIEW_MODE else 3
    for _ in range(blob_count):
        blobs.append(
            {
                "x": rng.uniform(WIDTH * 0.15, WIDTH * 0.85),
                "y": rng.uniform(HEIGHT * 0.08, HEIGHT * 0.78),
                "radius": rng.randint(140, 260) if PREVIEW_MODE else rng.randint(220, 420),
                "phase": rng.uniform(0, math.pi * 2),
                "color": rng.choice((theme["accent"], theme["accent_secondary"])),
            }
        )

    shooting_star_time = rng.uniform(total_duration * 0.30, total_duration * 0.70) if total_duration > 2 else None
    return {"stars": stars, "blobs": blobs, "shooting_star_time": shooting_star_time}


def draw_nebula_blobs(frame: Image.Image, particles: dict, t: float) -> Image.Image:
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    for blob in particles["blobs"]:
        alpha = int(30 + 24 * (0.5 + 0.5 * math.sin(t * 0.55 + blob["phase"])))
        blob_img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(blob_img)
        radius = blob["radius"]
        draw.ellipse(
            (blob["x"] - radius, blob["y"] - radius, blob["x"] + radius, blob["y"] + radius),
            fill=(*blob["color"], alpha),
        )
        blob_img = blob_img.filter(ImageFilter.GaussianBlur(radius // 5))
        overlay = Image.alpha_composite(overlay, blob_img)
    return Image.alpha_composite(frame.convert("RGBA"), overlay)


def draw_star_layers(frame: Image.Image, particles: dict, theme_key: str, t: float, total_duration: float) -> Image.Image:
    theme = TOPIC_THEMES[theme_key]
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    duration = max(total_duration, 0.01)

    for depth, layer in enumerate(particles["stars"], start=1):
        for star in layer:
            x = (star["x"] + star["speed_x"] * (t / duration) * duration) % WIDTH
            y = (star["y"] + star["speed_y"] * (t / duration) * duration) % HEIGHT
            twinkle = 0.6 + 0.4 * math.sin(t * (depth + 1.5) + star["x"] * 0.01)
            alpha = int(star["alpha"] * twinkle)
            base_color = tuple(min(255, int(theme["star_tint"][idx] * 0.55 + 255 * 0.45)) for idx in range(3))
            radius = star["size"] + depth * 0.1
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*base_color, alpha))

    result = Image.alpha_composite(frame.convert("RGBA"), overlay)
    shooting_star_time = particles.get("shooting_star_time")
    if shooting_star_time is not None:
        elapsed = t - shooting_star_time
        if 0 <= elapsed <= 0.65:
            streak = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            streak_draw = ImageDraw.Draw(streak)
            progress = elapsed / 0.65
            x = WIDTH * (0.18 + 0.60 * progress)
            y = HEIGHT * (0.18 + 0.22 * progress)
            for idx in range(16):
                length = 16 - idx
                alpha = int(220 * (1 - idx / 16) * (1 - progress * 0.45))
                streak_draw.line(
                    (x - idx * 14, y - idx * 5, x - idx * 14 + length * 2, y - idx * 5 + length * 0.5),
                    fill=(255, 255, 255, alpha),
                    width=max(1, 4 - idx // 5),
                )
            result = Image.alpha_composite(result, streak)
    return result.convert("RGBA")


def compose_background(base_background: Image.Image, particles: dict, theme_key: str, t: float, total_duration: float) -> Image.Image:
    frame = base_background.copy()
    frame = draw_nebula_blobs(frame, particles, t)
    frame = draw_star_layers(frame.convert("RGB"), particles, theme_key, t, total_duration)
    frame = add_color_wash(frame, theme_key, t)
    return frame.convert("RGBA")


def apply_screen_effects(frame: Image.Image, effects: list[str], frame_index: int) -> Image.Image:
    result = frame.convert("RGBA")
    if "camera_shake" in effects:
        rng = random.Random(frame_index)
        shifted = Image.new("RGBA", result.size, (0, 0, 0, 255))
        shifted.paste(result, (rng.randint(-10, 10), rng.randint(-8, 8)))
        result = shifted
    if "chromatic_aberration" in effects:
        r, g, b, a = result.split()
        r = r.transform(result.size, Image.AFFINE, (1, 0, -3, 0, 1, 0))
        b = b.transform(result.size, Image.AFFINE, (1, 0, 3, 0, 1, 0))
        result = Image.merge("RGBA", (r, g, b, a))
    if "flash" in effects:
        white = Image.new("RGBA", result.size, (255, 255, 255, 90))
        result = Image.alpha_composite(result, white)
    if "vignette_pulse" in effects:
        pulse = 70 + int(26 * math.sin(frame_index / FPS * 4))
        edge = Image.new("RGBA", result.size, (0, 0, 0, 0))
        edge_draw = ImageDraw.Draw(edge)
        edge_draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(0, 0, 0, pulse))
        cutout = Image.new("L", result.size, 255)
        cutout_draw = ImageDraw.Draw(cutout)
        cutout_draw.ellipse((120, 200, WIDTH - 120, HEIGHT - 260), fill=0)
        edge.putalpha(cutout.filter(ImageFilter.GaussianBlur(80)))
        result = Image.alpha_composite(result, edge)
    if "glitch" in effects:
        rng = random.Random(frame_index * 17)
        band_y = rng.randint(120, HEIGHT - 180)
        band_height = rng.randint(18, 48)
        strip = result.crop((0, band_y, WIDTH, band_y + band_height))
        result.paste(strip, (rng.randint(-22, 22), band_y))
    if "speed_lines" in effects:
        lines = Image.new("RGBA", result.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(lines)
        for idx in range(14 if PREVIEW_MODE else 24):
            y = int((idx + 1) * HEIGHT / (16 if PREVIEW_MODE else 28))
            alpha = 28 + (idx % 5) * 10
            ld.line((WIDTH * 0.08, y, WIDTH * 0.92, y - 40), fill=(255, 255, 255, alpha), width=2)
        lines = lines.filter(ImageFilter.GaussianBlur(2))
        result = Image.alpha_composite(result, lines)
    if "energy_burst" in effects:
        burst = Image.new("RGBA", result.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(burst)
        cx = WIDTH // 2
        cy = HEIGHT // 2
        for idx in range(12):
            angle = math.radians((frame_index * 3 + idx * 30) % 360)
            inner = 80
            outer = 420 if not PREVIEW_MODE else 260
            x1 = cx + math.cos(angle) * inner
            y1 = cy + math.sin(angle) * inner
            x2 = cx + math.cos(angle) * outer
            y2 = cy + math.sin(angle) * outer
            bd.line((x1, y1, x2, y2), fill=(255, 220, 120, 72), width=5)
        burst = burst.filter(ImageFilter.GaussianBlur(4))
        result = Image.alpha_composite(result, burst)
    if "lens_pulse" in effects:
        pulse = Image.new("RGBA", result.size, (0, 0, 0, 0))
        pd = ImageDraw.Draw(pulse)
        alpha = int(40 + 30 * math.sin(frame_index / max(FPS, 1) * 3.5))
        pd.ellipse((WIDTH * 0.18, HEIGHT * 0.12, WIDTH * 0.82, HEIGHT * 0.76), outline=(255, 255, 255, alpha), width=6)
        pulse = pulse.filter(ImageFilter.GaussianBlur(5))
        result = Image.alpha_composite(result, pulse)
    if "star_swirl" in effects:
        swirl = Image.new("RGBA", result.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(swirl)
        for idx in range(32 if PREVIEW_MODE else 56):
            angle = frame_index * 0.05 + idx * 0.24
            radius = 60 + idx * (8 if PREVIEW_MODE else 10)
            x = WIDTH / 2 + math.cos(angle) * radius
            y = HEIGHT / 2 + math.sin(angle) * radius * 0.52
            sd.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 255, 255, 95))
        swirl = swirl.filter(ImageFilter.GaussianBlur(1))
        result = Image.alpha_composite(result, swirl)
    return result


def glow_color_for_planet(name: str, theme_key: str) -> tuple[int, int, int]:
    theme = TOPIC_THEMES[theme_key]
    defaults = {
        "earth": (72, 150, 255),
        "mars": (255, 123, 89),
        "jupiter": (255, 185, 126),
        "saturn": (245, 216, 162),
        "sun": (255, 198, 56),
        "moon": (215, 219, 235),
        "neptune": (98, 153, 255),
        "venus": (255, 198, 120),
        "mercury": (190, 170, 150),
        "black_hole": theme["accent"],
        "neutron_star": (213, 225, 255),
    }
    return defaults.get(name, theme["planet_glow"])


def base_color_for_planet(name: str) -> tuple[int, int, int]:
    colors = {
        "earth": (52, 118, 214),
        "mars": (211, 96, 67),
        "jupiter": (219, 177, 135),
        "saturn": (228, 200, 148),
        "sun": (255, 192, 58),
        "moon": (192, 192, 198),
        "black_hole": (8, 8, 10),
        "neutron_star": (218, 226, 255),
        "neptune": (82, 129, 230),
        "venus": (232, 188, 114),
        "mercury": (171, 156, 142),
    }
    return colors.get(name, (150, 150, 150))


def soften_color(color: tuple[int, int, int], lift: int) -> tuple[int, int, int]:
    return tuple(min(255, component + lift) for component in color)


def draw_planet_body(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, name: str) -> None:
    base_fill = base_color_for_planet(name)
    if name == "earth":
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=base_fill)
        land = (79, 167, 114)
        draw.ellipse((cx - radius * 0.68, cy - radius * 0.52, cx - radius * 0.08, cy + radius * 0.14), fill=land)
        draw.ellipse((cx + radius * 0.14, cy - radius * 0.40, cx + radius * 0.58, cy + radius * 0.15), fill=land)
        draw.ellipse((cx + radius * 0.10, cy + radius * 0.06, cx + radius * 0.48, cy + radius * 0.52), fill=land)
        return
    if name == "mars":
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=base_fill)
        draw.arc((cx - radius * 0.65, cy - radius * 0.12, cx + radius * 0.55, cy + radius * 0.52), 210, 340, fill=(235, 154, 120), width=max(3, radius // 16))
        return
    if name == "jupiter":
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=base_fill)
        band_colors = ((184, 142, 103), (229, 194, 150))
        for band in range(7):
            band_y = cy - radius + band * (2 * radius / 7)
            color = band_colors[band % 2]
            for line_idx in range(int(radius / 5)):
                y = band_y + line_idx
                dist = abs(y - cy)
                if dist < radius:
                    half = int(math.sqrt(radius * radius - dist * dist))
                    draw.line((cx - half, y, cx + half, y), fill=color)
        draw.ellipse((cx + radius * 0.16, cy + radius * 0.08, cx + radius * 0.45, cy + radius * 0.25), fill=(189, 111, 89))
        return
    if name == "saturn":
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=base_fill)
        for stripe in range(4):
            y = cy - radius * 0.42 + stripe * radius * 0.28
            draw.arc((cx - radius * 0.88, y - radius * 0.12, cx + radius * 0.88, y + radius * 0.12), 180, 360, fill=soften_color(base_fill, 18), width=max(2, radius // 24))
        return
    if name == "sun":
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=base_fill)
        for flare in range(4):
            flare_r = radius * (0.72 - flare * 0.12)
            draw.ellipse((cx - flare_r, cy - flare_r, cx + flare_r, cy + flare_r), outline=(255, 227, 120, 140), width=max(2, radius // 20))
        return
    if name == "moon":
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=base_fill)
        for crater_x, crater_y, scale in ((-0.24, -0.10, 0.14), (0.18, 0.12, 0.12), (-0.05, 0.30, 0.10)):
            cr = radius * scale
            draw.ellipse(
                (cx + crater_x * radius - cr, cy + crater_y * radius - cr, cx + crater_x * radius + cr, cy + crater_y * radius + cr),
                fill=(148, 148, 154),
            )
        return
    if name == "black_hole":
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=base_fill)
        return
    if name == "neutron_star":
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=base_fill)
        draw.ellipse((cx - radius * 0.55, cy - radius * 0.55, cx + radius * 0.55, cy + radius * 0.55), fill=soften_color(base_fill, 20))
        return
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=base_fill)


def draw_saturn_rings(planet_layer: Image.Image, cx: int, cy: int, radius: int) -> None:
    rings = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(rings)
    ring_color = (229, 208, 167, 170)
    inner_box = (cx - radius * 1.55, cy - radius * 0.42, cx + radius * 1.55, cy + radius * 0.42)
    outer_box = (cx - radius * 1.75, cy - radius * 0.48, cx + radius * 1.75, cy + radius * 0.48)
    draw.ellipse(outer_box, outline=ring_color, width=max(5, radius // 10))
    draw.ellipse(inner_box, outline=(196, 171, 130, 185), width=max(3, radius // 14))
    rotated = rings.rotate(-17, resample=Image.Resampling.BICUBIC, center=(cx, cy))
    planet_layer.alpha_composite(rotated)


def draw_black_hole_accretion_disk(planet_layer: Image.Image, cx: int, cy: int, radius: int) -> None:
    disk = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(disk)
    colors = ((255, 73, 55, 120), (255, 136, 40, 160), (255, 209, 92, 200))
    for idx, color in enumerate(colors, start=1):
        pad_x = radius * (1.20 + idx * 0.12)
        pad_y = radius * (0.38 + idx * 0.06)
        draw.ellipse((cx - pad_x, cy - pad_y, cx + pad_x, cy + pad_y), outline=color, width=max(4, radius // 18))
    rotated = disk.rotate(-10, resample=Image.Resampling.BICUBIC, center=(cx, cy))
    planet_layer.alpha_composite(rotated)


def draw_sun_corona(planet_layer: Image.Image, cx: int, cy: int, radius: int, t: float) -> None:
    rays = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(rays)
    rotation = t * 14
    for idx in range(8):
        angle = math.radians(rotation + idx * 45)
        start_x = cx + math.cos(angle) * radius * 1.08
        start_y = cy + math.sin(angle) * radius * 1.08
        end_x = cx + math.cos(angle) * radius * 1.45
        end_y = cy + math.sin(angle) * radius * 1.45
        alpha = int(90 + 60 * math.sin(t * 1.5 + idx))
        draw.line((start_x, start_y, end_x, end_y), fill=(255, 194, 92, alpha), width=max(4, radius // 18))
    rays = rays.filter(ImageFilter.GaussianBlur(4))
    planet_layer.alpha_composite(rays)


def draw_planet_glow(planet_layer: Image.Image, cx: int, cy: int, radius: int, glow_color: tuple[int, int, int], t: float) -> None:
    pulse = 1.0 + 0.05 * math.sin(t * 3.0)
    for step in range(6, 0, -1):
        glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(glow)
        expand = radius * (1.08 + step * 0.08) * pulse
        alpha = int(34 * (1 - step / 7))
        draw.ellipse((cx - expand, cy - expand, cx + expand, cy + expand), fill=(*glow_color, alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(10 + step * 3))
        planet_layer.alpha_composite(glow)


def draw_highlight(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int) -> None:
    hx = cx - radius * 0.36
    hy = cy - radius * 0.34
    for idx in range(max(4, radius // 10), 0, -2):
        alpha = int(140 * (1 - idx / max(4, radius // 10)))
        draw.ellipse((hx - idx * 2, hy - idx * 2, hx + idx * 2, hy + idx * 2), fill=(255, 255, 255, alpha))


def blink_strength(name: str, t: float, expression: str) -> float:
    seed = int(hashlib.md5(f"{name}:{expression}".encode("utf-8")).hexdigest()[:6], 16) / 0xFFFFFF
    cycle = (t * 0.42 + seed) % 1.0
    blink = 0.0
    for center in (0.08, 0.46, 0.84):
        distance = abs(cycle - center)
        if distance < 0.045:
            blink = max(blink, 1 - distance / 0.045)
    return clamp(blink, 0.0, 1.0)


def gaze_offset_for_planet(name: str, expression: str, t: float) -> tuple[float, float]:
    base_offsets = {
        "looking_left": (-0.30, 0.0),
        "looking_right": (0.30, 0.0),
        "thinking": (0.18, -0.20),
        "smug": (0.18, 0.10),
        "scared": (0.06, -0.06),
        "shocked": (0.0, -0.04),
    }
    base_x, base_y = base_offsets.get(expression, (0.0, 0.0))
    seed = int(hashlib.md5(f"gaze:{name}".encode("utf-8")).hexdigest()[:6], 16) / 0xFFFFFF
    drift_x = math.sin(t * 0.9 + seed * math.pi * 2) * 0.08
    drift_y = math.cos(t * 0.7 + seed * math.pi) * 0.05
    return clamp(base_x + drift_x, -0.36, 0.36), clamp(base_y + drift_y, -0.24, 0.24)


def draw_eyes(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, expression: str, name: str, t: float) -> None:
    eye_y = cy - radius * 0.10
    spacing = radius * 0.31
    eye_radius = max(10, int(radius * 0.22))
    pupil_radius = max(4, int(eye_radius * 0.46))
    white_color = (255, 255, 230) if name == "sun" else (255, 255, 255)
    pupil_offset = gaze_offset_for_planet(name, expression, t)
    blink = blink_strength(name, t, expression)

    for idx, ex in enumerate((cx - spacing, cx + spacing)):
        if expression == "happy":
            draw.arc((ex - eye_radius, eye_y - eye_radius, ex + eye_radius, eye_y + eye_radius), 200, 340, fill=(0, 0, 0, 255), width=max(3, eye_radius // 3))
            continue
        if expression == "dead":
            draw.line((ex - eye_radius, eye_y - eye_radius, ex + eye_radius, eye_y + eye_radius), fill=(0, 0, 0, 255), width=4)
            draw.line((ex - eye_radius, eye_y + eye_radius, ex + eye_radius, eye_y - eye_radius), fill=(0, 0, 0, 255), width=4)
            continue
        scale = 1.58 if expression in {"scared", "shocked"} else 1.0
        scaled_eye = eye_radius * scale
        eyelid = max(3, scaled_eye * (1 - 0.90 * blink))
        draw.ellipse((ex - scaled_eye, eye_y - eyelid, ex + scaled_eye, eye_y + eyelid), fill=white_color, outline=(0, 0, 0, 255), width=max(2, int(radius * 0.025)))
        if expression == "angry":
            if idx == 0:
                draw.line((ex - scaled_eye - 4, eye_y - scaled_eye + 4, ex + scaled_eye + 4, eye_y - scaled_eye - 8), fill=(0, 0, 0, 255), width=4)
            else:
                draw.line((ex - scaled_eye - 4, eye_y - scaled_eye - 8, ex + scaled_eye + 4, eye_y - scaled_eye + 4), fill=(0, 0, 0, 255), width=4)
        if blink > 0.72:
            draw.line((ex - scaled_eye * 0.92, eye_y, ex + scaled_eye * 0.92, eye_y), fill=(0, 0, 0, 255), width=max(3, int(radius * 0.03)))
            continue
        pupil_size = pupil_radius * (0.45 if expression in {"scared", "shocked"} else 1.0)
        px = ex + pupil_offset[0] * scaled_eye
        py = eye_y + pupil_offset[1] * eyelid
        draw.ellipse((px - pupil_size, py - pupil_size, px + pupil_size, py + pupil_size), fill=(0, 0, 0, 255))
        shine = max(2, int(pupil_size // 2))
        draw.ellipse((px - pupil_size * 0.55 - shine, py - pupil_size * 0.55 - shine, px - pupil_size * 0.55 + shine, py - pupil_size * 0.55 + shine), fill=(255, 255, 255, 255))
        draw.ellipse((ex - scaled_eye * 0.92, eye_y - scaled_eye * 0.96, ex - scaled_eye * 0.40, eye_y - scaled_eye * 0.34), fill=(255, 255, 255, 82))


def draw_face_features(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, expression: str, name: str, t: float) -> None:
    mouth_y = cy + radius * 0.30 + math.sin(t * 1.8 + cx * 0.01) * radius * 0.02
    mouth_w = radius * 0.58
    if expression in {"happy", "excited", "smug"}:
        draw.arc((cx - mouth_w * 0.5, mouth_y - radius * 0.14, cx + mouth_w * 0.5, mouth_y + radius * 0.20), 10, 170, fill=(30, 20, 20, 255), width=max(3, radius // 16))
    elif expression in {"scared", "shocked"}:
        draw.ellipse((cx - radius * 0.13, mouth_y - radius * 0.11, cx + radius * 0.13, mouth_y + radius * 0.15), outline=(20, 15, 18, 255), width=max(3, radius // 16))
    elif expression == "angry":
        draw.arc((cx - mouth_w * 0.45, mouth_y - radius * 0.02, cx + mouth_w * 0.45, mouth_y + radius * 0.12), 190, 350, fill=(30, 20, 20, 255), width=max(3, radius // 16))
    else:
        draw.arc((cx - mouth_w * 0.40, mouth_y, cx + mouth_w * 0.40, mouth_y + radius * 0.10), 205, 335, fill=(30, 20, 20, 220), width=max(2, radius // 22))

    if expression in {"happy", "excited", "scared"} and name != "black_hole":
        blush = max(8, int(radius * 0.10))
        for bx in (cx - radius * 0.45, cx + radius * 0.45):
            draw.ellipse((bx - blush, cy + radius * 0.08 - blush, bx + blush, cy + radius * 0.08 + blush), fill=(255, 120, 150, 64))

    if expression in {"angry", "thinking", "smug"}:
        brow_y = cy - radius * 0.34
        tilt = -radius * 0.08 if expression == "angry" else radius * 0.03
        draw.line((cx - radius * 0.52, brow_y + tilt, cx - radius * 0.14, brow_y - tilt), fill=(15, 15, 18, 255), width=max(3, radius // 20))
        draw.line((cx + radius * 0.14, brow_y - tilt, cx + radius * 0.52, brow_y + tilt), fill=(15, 15, 18, 255), width=max(3, radius // 20))


def draw_planet_outline(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int) -> None:
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(255, 255, 255, 110), width=max(2, radius // 20))


def draw_planet_stickers(planet_layer: Image.Image, cx: int, cy: int, radius: int, name: str, theme_key: str, t: float) -> None:
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    accent = TOPIC_THEMES[theme_key]["accent"]
    if name in {"earth", "mars", "venus", "neptune"}:
        for idx in range(3):
            angle = t * 0.9 + idx * 2.0
            x = cx + math.cos(angle) * radius * 0.95
            y = cy + math.sin(angle) * radius * 0.75
            r = max(3, radius // 18)
            draw.ellipse((x - r, y - r, x + r, y + r), fill=(*accent, 90))
    if name == "sun":
        for idx in range(6):
            angle = t * 1.1 + idx * (math.pi / 3)
            x = cx + math.cos(angle) * radius * 1.18
            y = cy + math.sin(angle) * radius * 1.18
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 240, 150, 115))
    if name == "black_hole":
        draw.arc((cx - radius * 1.55, cy - radius * 0.72, cx + radius * 1.55, cy + radius * 0.72), 15, 195, fill=(*accent, 120), width=max(3, radius // 16))
    overlay = overlay.filter(ImageFilter.GaussianBlur(2))
    planet_layer.alpha_composite(overlay)


def draw_orbit_sparkles(planet_layer: Image.Image, cx: int, cy: int, radius: int, t: float, glow_color: tuple[int, int, int]) -> None:
    sparkles = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sparkles)
    for idx in range(6):
        angle = t * 1.8 + idx * (math.pi / 3)
        orbit_x = cx + math.cos(angle) * radius * 1.45
        orbit_y = cy + math.sin(angle) * radius * 0.95
        sparkle_r = max(2, radius // 24)
        sd.ellipse((orbit_x - sparkle_r, orbit_y - sparkle_r, orbit_x + sparkle_r, orbit_y + sparkle_r), fill=(*glow_color, 150))
        sd.line((orbit_x - sparkle_r * 2, orbit_y, orbit_x + sparkle_r * 2, orbit_y), fill=(255, 255, 255, 120), width=1)
        sd.line((orbit_x, orbit_y - sparkle_r * 2, orbit_x, orbit_y + sparkle_r * 2), fill=(255, 255, 255, 120), width=1)
    sparkles = sparkles.filter(ImageFilter.GaussianBlur(1))
    planet_layer.alpha_composite(sparkles)


def render_planet(layer: dict, theme_key: str, scene_progress: float, global_t: float) -> Image.Image:
    base_radius = SIZES.get(layer.get("size", "medium"), 150)
    x_norm, y_norm = POSITIONS.get(layer.get("position", "center"), POSITIONS["center"])
    cx = int(WIDTH * x_norm)
    cy = int(HEIGHT * y_norm)
    entry_animation = layer.get("entry_animation", "none")
    scale = 1.0
    offset_x = 0
    offset_y = 0
    if entry_animation != "none":
        p = clamp(scene_progress / 0.32, 0.0, 1.0)
        if entry_animation == "pop_in":
            scale *= ease_out_back(p)
        elif entry_animation == "slide_from_left":
            offset_x -= int((1 - ease_out_cubic(p)) * WIDTH * 0.5)
        elif entry_animation == "slide_from_right":
            offset_x += int((1 - ease_out_cubic(p)) * WIDTH * 0.5)
        elif entry_animation == "zoom_in":
            scale *= 0.60 + 0.40 * ease_out_cubic(p)
        elif entry_animation == "bounce_in":
            scale *= 0.70 + 0.30 * ease_out_back(p)
    effects = layer.get("effects", [])
    scale *= 1.0 + 0.025 * math.sin(global_t * 1.9 + cx * 0.008)
    if "pulse" in effects:
        scale *= 1.0 + 0.05 * math.sin(global_t * 4.0)
    if "shake" in effects:
        rng = random.Random(int(global_t * FPS * 9))
        offset_x += rng.randint(-8, 8)
        offset_y += rng.randint(-8, 8)
    offset_x += int(math.sin(global_t * 0.7 + cy * 0.01) * (5 if ("idle_bounce" in effects or "float" in effects) else 2))
    offset_y += int(math.sin(global_t * 1.6 + cx * 0.01) * (16 if ("idle_bounce" in effects or "float" in effects) else 10))
    cx += offset_x
    cy += offset_y
    radius = max(14, int(base_radius * scale))
    name = layer.get("name", "earth")
    expression = layer.get("expression", "neutral")
    glow_color = glow_color_for_planet(name, theme_key)
    planet_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw_planet_glow(planet_layer, cx, cy, radius, glow_color, global_t)
    if name == "saturn":
        draw_saturn_rings(planet_layer, cx, cy, radius)
    if name == "black_hole":
        draw_black_hole_accretion_disk(planet_layer, cx, cy, radius)
    if name == "sun":
        draw_sun_corona(planet_layer, cx, cy, radius, global_t)
    if "orbit_sparkles" in effects:
        draw_orbit_sparkles(planet_layer, cx, cy, radius, global_t, glow_color)
    body = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    body_draw = ImageDraw.Draw(body)
    draw_planet_body(body_draw, cx, cy, radius, name)
    draw_planet_outline(body_draw, cx, cy, radius)
    draw_highlight(body_draw, cx, cy, radius)
    draw_eyes(body_draw, cx, cy, radius, expression, name, global_t)
    draw_face_features(body_draw, cx, cy, radius, expression, name, global_t)
    body = body.filter(ImageFilter.GaussianBlur(0.15))
    planet_layer.alpha_composite(body)
    draw_planet_stickers(planet_layer, cx, cy, radius, name, theme_key, global_t)
    return planet_layer


def classify_word(word: str) -> str:
    clean = word.lower().strip(".,!?;:()[]{}")
    if any(ch.isdigit() for ch in word):
        return "number"
    if clean in PLANET_NAMES or clean.replace(" ", "_") in PLANET_NAMES:
        return "planet"
    if word.isupper() and len(word) > 2:
        return "accent"
    return "base"


def segment_style(word: str, base_size: int, theme_key: str) -> tuple[ImageFont.ImageFont, tuple[int, int, int], tuple[int, int, int]]:
    theme = TOPIC_THEMES[theme_key]
    kind = classify_word(word)
    if kind == "number":
        return get_font(int(base_size * 1.20)), NUMBER_YELLOW, NUMBER_YELLOW
    if kind == "planet":
        return get_font(base_size), PLANET_CYAN, PLANET_CYAN
    if kind == "accent":
        return get_font(base_size), theme["accent"], theme["accent"]
    return get_font(base_size), WHITE, theme["accent_secondary"]


def wrap_segments(content: str, base_size: int, max_width: int, theme_key: str) -> list[list[dict]]:
    measure = ImageDraw.Draw(Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0)))
    words = content.split()
    lines: list[list[dict]] = []
    current: list[dict] = []
    current_width = 0
    space_width = max(10, int(base_size * 0.22))
    for word in words:
        font, color, glow = segment_style(word, base_size, theme_key)
        bbox = measure.textbbox((0, 0), word, font=font)
        width = bbox[2] - bbox[0]
        leading_space = 0 if not current else space_width
        segment = {
            "text": word,
            "width": width,
            "leading_space": leading_space,
            "token_width": leading_space + width,
            "font": font,
            "color": color,
            "glow": glow,
        }
        if current and current_width + segment["token_width"] > max_width:
            lines.append(current)
            segment["leading_space"] = 0
            segment["token_width"] = width
            current = [segment]
            current_width = width
        else:
            current.append(segment)
            current_width += segment["token_width"]
    if current:
        lines.append(current)
    return lines


def line_width(line: list[dict]) -> int:
    return sum(segment["token_width"] for segment in line)


def fit_text_layout(content: str, initial_size: int, theme_key: str, *, max_lines: int = 4) -> tuple[int, list[list[dict]]]:
    font_size = initial_size
    while font_size >= 26:
        lines = wrap_segments(content, font_size, WIDTH - 120, theme_key)
        widest = max((line_width(line) for line in lines), default=0)
        if len(lines) <= max_lines and widest <= WIDTH - 80:
            return font_size, lines
        font_size -= 2
    final_lines = wrap_segments(content, 26, WIDTH - 96, theme_key)
    return 26, final_lines[:max_lines]


def rendered_content_for_style(content: str, style: str, progress: float) -> str:
    if not content:
        return ""
    if style == "typewriter":
        chars = max(1, int(len(content) * clamp(progress * 1.25, 0.0, 1.0)))
        return content[:chars]
    if style == "word_by_word":
        words = content.split()
        count = max(1, int(len(words) * clamp(progress * 1.35, 0.0, 1.0)))
        return " ".join(words[:count])
    return content


def draw_text_block(frame: Image.Image, text_config: dict, scene_progress: float, theme_key: str) -> Image.Image:
    content = text_config.get("content", "").strip()
    if not content:
        return frame
    style = text_config.get("style", "word_by_word")
    position = text_config.get("position", "top")
    visible_text = rendered_content_for_style(content, style, scene_progress)
    if not visible_text:
        return frame
    base_size = 68
    if style == "slam_in":
        zoom_progress = clamp(scene_progress / 0.18, 0.0, 1.0)
        base_size = int(68 * (1.55 - 0.55 * ease_out_back(zoom_progress)))
    base_size, lines = fit_text_layout(visible_text, base_size, theme_key, max_lines=5 if position == "top" else 4)
    if not lines:
        return frame

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    y_start = 150 if position == "top" else HEIGHT - 360
    line_spacing = int(base_size * 1.15)
    block_height = len(lines) * line_spacing
    if position == "bottom":
        y_start = max(110, HEIGHT - block_height - 150)
    entrance = ease_out_cubic(clamp(scene_progress / 0.22, 0.0, 1.0))
    y_offset = int((1 - entrance) * 30)
    for line_index, line in enumerate(lines):
        current_line_width = line_width(line)
        x = max(36, min((WIDTH - current_line_width) // 2, WIDTH - current_line_width - 36))
        line_y = y_start + line_index * line_spacing + y_offset
        font_heights = [segment["font"].size if hasattr(segment["font"], "size") else base_size for segment in line]
        pill_height = int(max(font_heights) + 16)
        pill_left = max(18, x - 10)
        pill_right = min(WIDTH - 18, x + current_line_width + 10)
        draw.rounded_rectangle((pill_left, line_y - 8, pill_right, line_y + pill_height), radius=18, fill=PILL_DARK)
        cursor_x = x
        for segment in line:
            font = segment["font"]
            text = segment["text"]
            color = segment["color"]
            glow = segment["glow"]
            cursor_x += segment["leading_space"]
            glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_layer)
            for offset in (5, 3):
                alpha = 28 if offset == 5 else 52
                for dx in (-offset, 0, offset):
                    for dy in (-offset, 0, offset):
                        glow_draw.text((cursor_x + dx, line_y + dy), text, font=font, fill=(*glow, alpha))
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(4))
            overlay.alpha_composite(glow_layer)
            shadow_draw = ImageDraw.Draw(overlay)
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    shadow_draw.text((cursor_x + dx, line_y + dy), text, font=font, fill=(0, 0, 0, 255))
            shadow_draw.text((cursor_x, line_y), text, font=font, fill=(*color, 255))
            cursor_x += segment["width"]
    return Image.alpha_composite(frame.convert("RGBA"), overlay)


def apply_cinematic_camera(frame: Image.Image, scene: dict, progress: float, global_progress: float) -> Image.Image:
    seed = float(scene.get("time_start", 0.0)) * 0.37 + len(scene.get("layers", [])) * 0.19
    scale = 1.025 + 0.018 * math.sin(math.pi * progress)
    if scene.get("dramatic_moment"):
        scale += 0.02
    target_width = max(WIDTH + 2, int(WIDTH * scale))
    target_height = max(HEIGHT + 2, int(HEIGHT * scale))
    zoomed = frame.resize((target_width, target_height), Image.Resampling.LANCZOS)
    max_left = max(0, target_width - WIDTH)
    max_top = max(0, target_height - HEIGHT)
    left = int((max_left / 2) + math.sin(global_progress * 5.0 + seed) * max_left * 0.18)
    top = int((max_top / 2) + math.cos(global_progress * 4.1 + seed * 1.7) * max_top * 0.18)
    left = int(clamp(left, 0, max_left))
    top = int(clamp(top, 0, max_top))
    return zoomed.crop((left, top, left + WIDTH, top + HEIGHT)).convert("RGBA")


def draw_progress_bar(frame: Image.Image, progress: float, theme_key: str) -> None:
    theme = TOPIC_THEMES[theme_key]
    draw = ImageDraw.Draw(frame)
    bar_height = 8
    y = HEIGHT - bar_height
    draw.rectangle((0, y, WIDTH, HEIGHT), fill=(30, 32, 40, 220))
    fill_width = int(WIDTH * clamp(progress, 0.0, 1.0))
    if fill_width <= 0:
        return
    draw.rectangle((0, y, fill_width, HEIGHT), fill=(*theme["accent"], 255))
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((fill_width - 16, y - 10, fill_width + 16, HEIGHT + 10), fill=(*theme["accent"], 150))
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    frame.alpha_composite(glow)


def draw_hook_screen(base_background: Image.Image, particles: dict, hook_text: str, theme_key: str, t: float) -> Image.Image:
    frame = compose_background(base_background, particles, theme_key, t, HOOK_DURATION)
    theme = TOPIC_THEMES[theme_key]
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    scale = 0.60 + 0.40 * ease_out_back(clamp(t / 0.4, 0.0, 1.0))
    font_size = int(92 * scale)
    font_size, segmented_lines = fit_text_layout(hook_text, font_size, theme_key, max_lines=4)
    font = get_font(font_size)
    lines = [" ".join(segment["text"] for segment in line) for line in segmented_lines]
    line_height = int(font_size * 1.12)
    block_height = len(lines) * line_height
    start_y = HEIGHT // 2 - block_height // 2 - 70
    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        width = bbox[2] - bbox[0]
        x = (WIDTH - width) // 2
        y = start_y + idx * line_height
        draw.rounded_rectangle((x - 16, y - 12, x + width + 16, y + font_size + 8), radius=22, fill=(8, 10, 18, 165))
        glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        for spread in (10, 6):
            alpha = 24 if spread == 10 else 48
            for dx in (-spread, 0, spread):
                for dy in (-spread, 0, spread):
                    glow_draw.text((x + dx, y + dy), line, font=font, fill=(*theme["accent"], alpha))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(6))
        overlay.alpha_composite(glow_layer)
        shadow_draw = ImageDraw.Draw(overlay)
        for dx in (-3, -2, -1, 0, 1, 2, 3):
            for dy in (-3, -2, -1, 0, 1, 2, 3):
                shadow_draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
        shadow_draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
    underline_progress = ease_out_cubic(clamp(t / 0.6, 0.0, 1.0))
    underline_width = int((WIDTH * 0.52) * underline_progress)
    underline_x = (WIDTH - int(WIDTH * 0.52)) // 2
    underline_y = start_y + block_height + 36
    if underline_width > 0:
        draw.rounded_rectangle((underline_x, underline_y, underline_x + underline_width, underline_y + 6), radius=4, fill=theme["accent"])
    frame = Image.alpha_composite(frame.convert("RGBA"), overlay)
    draw_progress_bar(frame, t / max(HOOK_DURATION, 0.01), theme_key)
    return frame


def render_scene_frame(
    scene: dict,
    base_background: Image.Image,
    particles: dict,
    theme_key: str,
    local_t: float,
    scene_duration_value: float,
    *,
    global_progress: float,
) -> Image.Image:
    frame = compose_background(base_background, particles, theme_key, local_t, scene_duration_value)
    progress = clamp(local_t / max(scene_duration_value, 0.01), 0.0, 1.0)
    scene_effects = list(scene.get("screen_effects", []))
    for effect in THEME_SCENE_EFFECTS.get(theme_key, []):
        if effect not in scene_effects and random.Random(f"{theme_key}:{scene.get('time_start', 0)}").random() > 0.45:
            scene_effects.append(effect)
    if scene.get("dramatic_moment"):
        for effect in ("lens_pulse", "energy_burst"):
            if effect not in scene_effects:
                scene_effects.append(effect)
    for layer in scene.get("layers", []):
        if layer.get("type") == "planet":
            frame.alpha_composite(render_planet(layer, theme_key, progress, local_t))
    frame = draw_text_block(frame, scene.get("text", {}), progress, theme_key)
    frame = apply_cinematic_camera(frame, scene, progress, global_progress)
    frame = apply_screen_effects(frame, scene_effects, int(local_t * FPS))
    draw_progress_bar(frame, global_progress, theme_key)
    return frame


def scene_duration(scene: dict) -> float:
    start = float(scene.get("time_start", 0.0))
    end = float(scene.get("time_end", start + 4.0))
    return max(0.5, end - start)


def transition_frame(current: Image.Image, next_frame: Image.Image, transition_type: str, progress: float) -> Image.Image:
    p = clamp(progress, 0.0, 1.0)
    if transition_type == "crossfade":
        return Image.blend(current.convert("RGBA"), next_frame.convert("RGBA"), p)
    if transition_type == "horizontal_wipe":
        wipe = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
        current_shift = int(-WIDTH * ease_in_out_cubic(p))
        next_shift = int(WIDTH * (1 - ease_in_out_cubic(p)))
        wipe.alpha_composite(current, (current_shift, 0))
        wipe.alpha_composite(next_frame, (next_shift, 0))
        return wipe
    if transition_type == "zoom_through":
        scale = 1.0 + 0.38 * ease_out_cubic(p)
        zoomed = current.resize((int(WIDTH * scale), int(HEIGHT * scale)), Image.Resampling.LANCZOS)
        left = (zoomed.width - WIDTH) // 2
        top = (zoomed.height - HEIGHT) // 2
        zoomed = zoomed.crop((left, top, left + WIDTH, top + HEIGHT)).convert("RGBA")
        if p > 0.55:
            zoomed = Image.blend(zoomed, next_frame.convert("RGBA"), clamp((p - 0.55) / 0.45, 0.0, 1.0))
        flash = Image.new("RGBA", (WIDTH, HEIGHT), (255, 255, 255, int(120 * math.sin(math.pi * p))))
        return Image.alpha_composite(zoomed, flash)
    return next_frame


def build_segment_plan(script_data: dict) -> tuple[list[dict], float]:
    timeline = script_data.get("timeline", [])
    has_hook = bool(script_data.get("idea", {}).get("hook"))
    segments = []
    elapsed = 0.0
    if has_hook:
        segments.append({"type": "hook", "start": 0.0, "end": HOOK_DURATION})
        elapsed += HOOK_DURATION
    for index, scene in enumerate(timeline):
        duration = scene_duration(scene)
        segments.append({"type": "scene", "scene_index": index, "start": elapsed, "end": elapsed + duration})
        elapsed += duration
        if index < len(timeline) - 1:
            segments.append(
                {
                    "type": "transition",
                    "scene_index": index,
                    "next_scene_index": index + 1,
                    "transition_type": TRANSITIONS[index % len(TRANSITIONS)],
                    "start": elapsed,
                    "end": elapsed + TRANSITION_DURATION,
                }
            )
            elapsed += TRANSITION_DURATION
    return segments, elapsed


def create_video(script_data: dict, output_path: Path) -> bool:
    timeline = script_data.get("timeline", [])
    if not timeline:
        print("No timeline found.")
        return False

    theme_key = infer_theme(script_data)
    topic_keyword = infer_topic_keyword(script_data)
    base_image, background_path = get_space_background(topic_keyword)
    base_background = build_base_background(base_image, theme_key)
    segments, total_duration = build_segment_plan(script_data)
    particles = build_particle_system(theme_key, topic_keyword, total_duration)
    mood = script_data.get("metadata", {}).get("music_style") or script_data.get("metadata", {}).get("mood") or "cinematic"
    music_path = get_music_for_mood(mood, total_duration)

    print(f"Renderer theme: {theme_key}")
    print(f"Topic keyword: {topic_keyword}")
    if background_path:
        print(f"Background source cache: {background_path}")
    if music_path:
        print(f"Music track: {music_path}")

    scene_cache: dict[tuple[int, int], np.ndarray] = {}

    def frame_for_scene(scene_index: int, local_t: float, global_progress: float) -> Image.Image:
        scene = timeline[scene_index]
        scene_len = scene_duration(scene)
        frame_key = (scene_index, int(clamp(local_t, 0.0, scene_len) * FPS))
        cached = scene_cache.get(frame_key)
        if cached is not None:
            return Image.fromarray(cached).convert("RGBA")
        rendered = render_scene_frame(scene, base_background, particles, theme_key, local_t, scene_len, global_progress=global_progress)
        scene_cache[frame_key] = np.array(rendered.convert("RGB"), dtype=np.uint8)
        return rendered

    def make_frame(t: float) -> np.ndarray:
        clamped_t = clamp(t, 0.0, max(total_duration - 1 / FPS, 0.0))
        for segment in segments:
            if segment["start"] <= clamped_t < segment["end"] or math.isclose(clamped_t, segment["end"]):
                global_progress = clamped_t / max(total_duration, 0.01)
                local_t = clamped_t - segment["start"]
                if segment["type"] == "hook":
                    frame = draw_hook_screen(base_background, particles, script_data.get("idea", {}).get("hook", ""), theme_key, local_t)
                elif segment["type"] == "scene":
                    frame = frame_for_scene(segment["scene_index"], local_t, global_progress)
                else:
                    current_index = segment["scene_index"]
                    next_index = segment["next_scene_index"]
                    progress = local_t / TRANSITION_DURATION
                    current_duration = scene_duration(timeline[current_index])
                    current_frame = frame_for_scene(current_index, max(current_duration - 1 / FPS, 0.0), global_progress)
                    next_frame = frame_for_scene(next_index, min(progress * 0.35, scene_duration(timeline[next_index])), global_progress)
                    frame = transition_frame(current_frame, next_frame, segment["transition_type"], progress)
                    draw_progress_bar(frame, global_progress, theme_key)
                return np.array(frame.convert("RGB"), dtype=np.uint8)
        fallback = draw_hook_screen(base_background, particles, script_data.get("idea", {}).get("hook", ""), theme_key, 0.0)
        return np.array(fallback.convert("RGB"), dtype=np.uint8)

    video = VideoClip(make_frame, duration=total_duration)
    audio_clip = None
    if music_path and Path(music_path).exists():
        try:
            audio_clip = AudioFileClip(music_path).fx(afx.audio_loop, duration=total_duration)
            audio_clip = audio_clip.subclip(0, total_duration).volumex(0.34)
            audio_clip = audio_clip.fx(afx.audio_fadein, 0.7).fx(afx.audio_fadeout, 1.2)
            video = video.set_audio(audio_clip)
        except Exception as exc:
            print(f"Audio attachment failed: {exc}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="ultrafast" if PREVIEW_MODE else "veryfast",
        threads=4,
        logger=None,
        bitrate="1800k" if PREVIEW_MODE else "5000k",
    )

    try:
        video.close()
        if audio_clip:
            audio_clip.close()
    except Exception:
        pass

    script_data["background_path"] = str(background_path) if background_path else None
    script_data["music_path"] = music_path
    return output_path.exists()


def process_scripts(*, preview: bool = False) -> None:
    return process_scripts_result(preview=preview)


def process_scripts_result(*, preview: bool = False) -> bool:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not SCRIPTS_DIR.exists():
        print(f"No scripts directory: {SCRIPTS_DIR}")
        return False
    scripts = sorted(path for path in SCRIPTS_DIR.glob("*.json"))
    if not scripts:
        print("No scripts to process.")
        return False

    if preview:
        scripts = sorted(scripts, key=lambda path: path.stat().st_mtime, reverse=True)[:1]

    rendered_any = False
    failed_any = False

    for script_path in scripts:
        try:
            script_data = json.loads(script_path.read_text(encoding="utf-8"))
            if script_data.get("rendered") and not preview:
                print(f"Skipping already rendered script: {script_path.name}")
                continue
            if preview:
                output_path = OUTPUT_DIR / f"{script_path.stem}_preview.mp4"
            else:
                output_path = OUTPUT_DIR / script_path.with_suffix(".mp4").name
            ok = create_video(script_data, output_path)
            if ok:
                rendered_any = True
                if preview:
                    script_data["preview_rendered_at"] = datetime.now().isoformat()
                    script_data["preview_video_path"] = str(output_path)
                else:
                    script_data["rendered"] = True
                    script_data["status"] = "rendered"
                    script_data["rendered_at"] = datetime.now().isoformat()
                    script_data["video_path"] = str(output_path)
                script_path.write_text(json.dumps(script_data, indent=2), encoding="utf-8")
                print(f"Rendered: {output_path}")
            else:
                failed_any = True
                print(f"Renderer did not produce output for {script_path.name}")
        except Exception as exc:
            failed_any = True
            print(f"Renderer failed for {script_path.name}: {exc}")
            import traceback
            traceback.print_exc()
    return rendered_any and not failed_any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Astro Shorts videos.")
    parser.add_argument("--preview", action="store_true", help="Render a faster low-resolution preview without marking the script as final.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_render_mode(preview=args.preview)
    print("=" * 60)
    print("ASTRO SHORTS V2 - Dark Cosmos Renderer")
    if PREVIEW_MODE:
        print("Preview mode enabled: 540x960 @ 12fps")
    print("=" * 60)
    ok = process_scripts_result(preview=PREVIEW_MODE)
    print("=" * 60)
    print("Render pass complete")
    print("=" * 60)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
