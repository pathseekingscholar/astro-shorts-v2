"""
Video Renderer - CINEMA EDITION
================================
Upgrades over V5:
- Parallax 3-layer starfield (depth)
- NASA APOD background image integration  
- Montserrat font with fallbacks
- Hook screen (first 2.5s, zoom-in punch)
- Progress bar at bottom
- Highlighted number text (yellow, larger, glow)
- Glow rings on all planets
- Shooting star effect
- Topic-based color themes
- All existing V5 features preserved
"""

import os
import json
import random
import math
import textwrap
import requests
from datetime import datetime
from moviepy.editor import VideoClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
import numpy as np

# =============================================================================
# CONFIG
# =============================================================================
WIDTH = 1080
HEIGHT = 1920
FPS = 30
SCRIPTS_DIR = "scripts_output"
OUTPUT_DIR = "videos_output"
AUDIO_DIR = "assets/audio"
FONTS_DIR = "assets/fonts"

COLORS = {
    'background':  (8,   8,  24),
    'text_white':  (255, 255, 255),
    'text_yellow': (255, 220,   0),
    'text_cyan':   (0,   255, 255),
    'text_red':    (255,  80,  80),
    'text_pink':   (255, 100, 200),
    'text_orange': (255, 160,  40),
    'glow_blue':   (0,   180, 255),
    'glow_pink':   (255, 100, 200),
    'glow_yellow': (255, 200,   0),
    'accent':      (255, 220,   0),
    'progress':    (255, 200,   0),
}

POSITIONS = {
    'center':       (0.5,  0.5),
    'left':         (0.28, 0.5),
    'right':        (0.72, 0.5),
    'top':          (0.5,  0.3),
    'bottom':       (0.5,  0.7),
    'top_left':     (0.28, 0.3),
    'top_right':    (0.72, 0.3),
    'bottom_left':  (0.28, 0.7),
    'bottom_right': (0.72, 0.7),
}

SIZES = {
    'tiny':   50,
    'small':  90,
    'medium': 150,
    'large':  210,
    'huge':   280,
}

# Topic → visual theme mapping
THEMES = {
    'scale':          {'nebula': (10, 20, 60), 'accent': (60, 140, 255),  'star_tint': (100, 160, 255)},
    'travel_time':    {'nebula': (5,  15, 50), 'accent': (80, 160, 255),  'star_tint': (120, 170, 255)},
    'planetary_facts':{'nebula': (30, 15, 5),  'accent': (255, 160, 40),  'star_tint': (255, 200, 100)},
    'hypothetical':   {'nebula': (20, 5,  40), 'accent': (200, 80, 255),  'star_tint': (180, 100, 255)},
    'myth_busting':   {'nebula': (5,  25, 15), 'accent': (0,   255, 160), 'star_tint': (80,  255, 160)},
    'cosmic_mystery': {'nebula': (30, 5,  30), 'accent': (255, 60,  180), 'star_tint': (255, 100, 200)},
    'extreme':        {'nebula': (40, 5,  5),  'accent': (255, 80,  40),  'star_tint': (255, 120,  80)},
    'default':        {'nebula': (15, 10, 35), 'accent': (255, 220,   0), 'star_tint': (180, 180, 255)},
}

# =============================================================================
# FONT LOADING
# =============================================================================
def get_font(size, bold=True):
    """Load Montserrat if available, else fallback chain."""
    font_candidates = []
    if bold:
        font_candidates = [
            os.path.join(FONTS_DIR, "Montserrat-ExtraBold.ttf"),
            os.path.join(FONTS_DIR, "Montserrat-Bold.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
    else:
        font_candidates = [
            os.path.join(FONTS_DIR, "Montserrat-Regular.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

# =============================================================================
# EASING
# =============================================================================
def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)

def ease_out_elastic(t):
    if t == 0 or t == 1: return t
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1

def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)

def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2

# =============================================================================
# NASA APOD BACKGROUND
# =============================================================================
def fetch_nasa_background(topic_keywords=""):
    """Try to fetch a NASA APOD image as background."""
    api_key = os.environ.get("NASA_API_KEY", "")
    if not api_key:
        return None
    try:
        resp = requests.get(
            f"https://api.nasa.gov/planetary/apod?api_key={api_key}&count=5",
            timeout=10
        )
        if resp.status_code != 200:
            return None
        items = resp.json()
        # Prefer images (not video)
        images = [i for i in items if i.get("media_type") == "image"]
        if not images:
            return None
        pick = random.choice(images)
        img_url = pick.get("url", "")
        if not img_url:
            return None
        img_resp = requests.get(img_url, timeout=15)
        if img_resp.status_code != 200:
            return None
        from io import BytesIO
        img = Image.open(BytesIO(img_resp.content)).convert("RGB")
        img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
        # Darken significantly so text stays readable
        img = ImageEnhance.Brightness(img).enhance(0.3)
        img = ImageEnhance.Contrast(img).enhance(0.7)
        print(f"🌌 NASA background: {pick.get('title','')[:40]}")
        return img
    except Exception as e:
        print(f"⚠️ NASA fetch failed: {e}")
        return None

# =============================================================================
# PARALLAX STARFIELD (3 depth layers)
# =============================================================================
def create_parallax_starfield(theme_key="default", seed=42, nasa_bg=None):
    """
    Returns a list of 3 starfield layers (far, mid, near) as numpy arrays.
    If nasa_bg provided, layer 0 is the NASA image.
    """
    theme = THEMES.get(theme_key, THEMES["default"])
    nebula_color = theme["nebula"]
    star_tint = theme["star_tint"]

    layers = []

    # --- Layer 0: deep background (or NASA image) ---
    if nasa_bg is not None:
        layers.append(np.array(nasa_bg, dtype=np.uint8))
    else:
        random.seed(seed)
        bg = Image.new("RGB", (WIDTH, HEIGHT), (5, 5, 18))
        draw = ImageDraw.Draw(bg)
        # Gradient
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(5 + nebula_color[0] * 0.15 * (1 - t))
            g = int(5 + nebula_color[1] * 0.15 * (1 - t))
            b = int(18 + nebula_color[2] * 0.3 * (1 - t))
            draw.line([(0, y), (WIDTH, y)], fill=(min(255,r), min(255,g), min(255,b)))
        # Nebula blobs
        for _ in range(3):
            cx = random.randint(0, WIDTH)
            cy = random.randint(0, HEIGHT)
            rad = random.randint(250, 550)
            for r in range(rad, 0, -25):
                af = 1.0 - (r / rad)
                c = tuple(int(nc * 0.18 * af) for nc in nebula_color)
                draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=c)
        # Distant stars (tiny, dim)
        for _ in range(400):
            x, y = random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)
            b = random.randint(40, 100)
            draw.point((x, y), fill=(b, b, min(255, b + 30)))
        layers.append(np.array(bg, dtype=np.uint8))

    # --- Layer 1: mid stars ---
    random.seed(seed + 1)
    mid = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mid)
    for _ in range(150):
        x, y = random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1)
        b = random.randint(100, 200)
        tc = star_tint
        color = (
            min(255, int(b * 0.5 + tc[0] * 0.5)),
            min(255, int(b * 0.5 + tc[1] * 0.5)),
            min(255, int(b * 0.5 + tc[2] * 0.5)),
            220,
        )
        sz = random.choice([1, 1, 2])
        draw.ellipse([x-sz, y-sz, x+sz, y+sz], fill=color)
    layers.append(np.array(mid, dtype=np.uint8))

    # --- Layer 2: foreground bright stars + glow ---
    random.seed(seed + 2)
    fg = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fg)
    for _ in range(35):
        x, y = random.randint(20, WIDTH-20), random.randint(20, HEIGHT-20)
        for r in range(7, 0, -1):
            intensity = int(60 + 195 * (1 - r / 7))
            draw.ellipse([x-r, y-r, x+r, y+r],
                         fill=(intensity, intensity, min(255, intensity+30), int(180 * (1 - r/7))))
        draw.ellipse([x-1, y-1, x+1, y+1], fill=(255, 255, 255, 255))
    # Lens flares
    for _ in range(5):
        x, y = random.randint(60, WIDTH-60), random.randint(60, HEIGHT-60)
        for d in range(-15, 16):
            i = int(160 * (1 - abs(d)/15))
            if i > 0:
                draw.point((x+d, y), fill=(i, i, i, i+80))
                draw.point((x, y+d), fill=(i, i, i, i+80))
        draw.ellipse([x-2, y-2, x+2, y+2], fill=(255, 255, 255, 255))
    layers.append(np.array(fg, dtype=np.uint8))

    return layers

def composite_parallax(layers, t, total_duration, shooting_star_t=None):
    """
    Composite the 3 parallax layers with drift.
    Layer 0 (bg): slowest drift
    Layer 1 (mid): medium drift  
    Layer 2 (fg): fastest drift
    Also renders shooting star if timing matches.
    """
    progress = t / max(total_duration, 0.001)

    # Start from layer 0 (RGB)
    base = Image.fromarray(layers[0], "RGB")

    # Mid layer drift (subtle horizontal + vertical)
    if layers[1].shape[2] == 4:
        mid = Image.fromarray(layers[1], "RGBA")
        dx_mid = int(math.sin(progress * math.pi * 2) * 8)
        dy_mid = int(-progress * 15)
        mid_shifted = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        mid_shifted.paste(mid, (dx_mid, dy_mid))
        base = base.convert("RGBA")
        base = Image.alpha_composite(base, mid_shifted)
        base = base.convert("RGB")

    # Foreground drift (faster)
    if layers[2].shape[2] == 4:
        fg = Image.fromarray(layers[2], "RGBA")
        dx_fg = int(math.sin(progress * math.pi * 2) * 18)
        dy_fg = int(-progress * 35)
        fg_shifted = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        fg_shifted.paste(fg, (dx_fg, dy_fg))
        base = base.convert("RGBA")
        base = Image.alpha_composite(base, fg_shifted)
        base = base.convert("RGB")

    # Shooting star
    if shooting_star_t is not None:
        elapsed = t - shooting_star_t
        if 0 <= elapsed < 0.6:
            frac = elapsed / 0.6
            draw = ImageDraw.Draw(base)
            sx = int(WIDTH * 0.1 + frac * WIDTH * 0.8)
            sy = int(HEIGHT * 0.15 + frac * HEIGHT * 0.25)
            tail_len = int(120 * (1 - frac))
            alpha_v = int(255 * (1 - frac))
            for i in range(tail_len):
                px = sx - i
                py = sy - int(i * 0.35)
                if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                    a = int(alpha_v * (1 - i / tail_len))
                    brightness = max(0, a)
                    draw.point((px, py), fill=(brightness, brightness, min(255, brightness + 40)))

    return base

# =============================================================================
# HOOK SCREEN
# =============================================================================
def render_hook_screen(hook_text, theme_key, layers, t, total_dur):
    """First 2.5s: big bold hook text, zoom-in entrance."""
    frame = composite_parallax(layers, t, total_dur)
    draw = ImageDraw.Draw(frame)
    theme = THEMES.get(theme_key, THEMES["default"])
    accent = theme["accent"]

    # Dark bar behind text
    bar_h = 400
    bar_y = HEIGHT // 2 - bar_h // 2
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, bar_y, WIDTH, bar_y + bar_h], fill=(0, 0, 0, 180))
    frame = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")

    # Zoom-in scale: 0 → 1.0 over 0.4s
    scale = min(ease_out_back(min(t / 0.4, 1.0)), 1.05)
    font_size = int(82 * scale)
    font_size = max(20, font_size)
    font = get_font(font_size)

    # Accent underline color for hook
    draw = ImageDraw.Draw(frame)

    # Word wrap
    lines = textwrap.wrap(hook_text, width=18)
    line_h = int(font_size * 1.25)
    total_h = len(lines) * line_h
    start_y = HEIGHT // 2 - total_h // 2

    for li, line in enumerate(lines):
        ly = start_y + li * line_h
        # Measure
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lx = (WIDTH - lw) // 2

        # Glow pass
        glow_layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        for off in [8, 5, 3]:
            a = int(30 * (1 - off / 10))
            for dx in range(-off, off+1, 3):
                for dy in range(-off, off+1, 3):
                    gd.text((lx+dx, ly+dy), line, font=font,
                             fill=(*accent, a))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(3))
        frame = Image.alpha_composite(frame.convert("RGBA"), glow_layer).convert("RGB")
        draw = ImageDraw.Draw(frame)

        # Outline
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                draw.text((lx+dx, ly+dy), line, font=font, fill=(0, 0, 0))
        # Text
        draw.text((lx, ly), line, font=font, fill=(255, 255, 255))

    # Accent bar at bottom of text block
    bar_bottom = start_y + total_h + 20
    acc_w = int(WIDTH * 0.5 * min(t / 0.8, 1.0))
    acc_x = (WIDTH - acc_w) // 2
    draw.rectangle([acc_x, bar_bottom, acc_x + acc_w, bar_bottom + 5],
                   fill=accent)

    return np.array(frame)

# =============================================================================
# PROGRESS BAR
# =============================================================================
def draw_progress_bar(frame_img, progress, theme_key="default"):
    """Draw a thin progress bar at the very bottom."""
    draw = ImageDraw.Draw(frame_img)
    theme = THEMES.get(theme_key, THEMES["default"])
    accent = theme["accent"]
    bar_y = HEIGHT - 12
    # Background track
    draw.rectangle([0, bar_y, WIDTH, HEIGHT], fill=(20, 20, 20))
    # Fill
    fill_w = int(WIDTH * min(progress, 1.0))
    if fill_w > 0:
        draw.rectangle([0, bar_y, fill_w, HEIGHT], fill=accent)
    # Glowing tip
    if fill_w > 4:
        tip_x = fill_w
        for i in range(8, 0, -1):
            a = int(180 * (1 - i / 8))
            draw.rectangle([tip_x - i, bar_y - i//2, tip_x + 2,
                            HEIGHT + i//2], fill=(*accent, a))

# =============================================================================
# PLANET DRAWING (with glow rings)
# =============================================================================
def draw_planet_with_glow(draw, cx, cy, radius, planet_type='earth',
                           expression='neutral', frame_num=0):
    """Draw planet with outer glow ring, then planet, then eyes."""

    # Glow rings
    glow_colors = {
        'earth':       (60, 140, 255),
        'mars':        (255, 100, 60),
        'jupiter':     (255, 180, 120),
        'saturn':      (220, 200, 150),
        'sun':         (255, 200, 50),
        'moon':        (200, 200, 220),
        'neptune':     (80, 140, 255),
        'venus':       (255, 200, 120),
        'black_hole':  (180, 60, 255),
        'neutron_star':(180, 180, 255),
    }
    glow_col = glow_colors.get(planet_type, (150, 150, 255))

    # Pulsing glow radius
    pulse = 1.0 + 0.04 * math.sin(frame_num / FPS * 2 * math.pi * 0.8)
    for i in range(6, 0, -1):
        r = int(radius * (1.15 + i * 0.06) * pulse)
        alpha = int(35 * (1 - i / 7))
        glow_img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_img)
        gd.ellipse([cx-r, cy-r, cx+r, cy+r],
                   fill=(*glow_col, alpha))
        # We'll composite this in render_frame

    # Draw the planet body
    planets = {
        'earth':        {'ocean': (40, 100, 180), 'land': (60, 140, 80)},
        'mars':         {'base': (180, 80, 60)},
        'jupiter':      {'base': (200, 160, 120), 'bands': [(180, 140, 100), (220, 180, 140)]},
        'saturn':       {'base': (210, 190, 150), 'ring': (180, 160, 130)},
        'sun':          {'base': (255, 200, 50)},
        'moon':         {'base': (180, 180, 180), 'crater': (140, 140, 140)},
        'neptune':      {'base': (60, 100, 200)},
        'venus':        {'base': (230, 180, 100)},
        'mercury':      {'base': (160, 150, 140)},
        'black_hole':   {'base': (10, 10, 10)},
        'neutron_star': {'base': (200, 200, 255)},
    }
    config = planets.get(planet_type, planets['earth'])

    if planet_type == 'sun':
        for i in range(8, 0, -1):
            r = radius + i * int(radius * 0.1)
            intensity = 255 - i * 22
            draw.ellipse([cx-r, cy-r, cx+r, cy+r],
                         fill=(intensity, int(intensity * 0.6), 0))
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                     fill=config['base'])

    elif planet_type == 'earth':
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                     fill=config['ocean'])
        land = config['land']
        draw.ellipse([cx-int(radius*0.7), cy-int(radius*0.5),
                      cx-int(radius*0.2), cy+int(radius*0.1)], fill=land)
        draw.ellipse([cx-int(radius*0.6), cy+int(radius*0.1),
                      cx-int(radius*0.3), cy+int(radius*0.5)], fill=land)
        draw.ellipse([cx+int(radius*0.1), cy-int(radius*0.4),
                      cx+int(radius*0.5), cy+int(radius*0.1)], fill=land)
        draw.ellipse([cx+int(radius*0.15), cy,
                      cx+int(radius*0.45), cy+int(radius*0.5)], fill=land)
        draw.ellipse([cx+int(radius*0.3), cy-int(radius*0.6),
                      cx+int(radius*0.7), cy-int(radius*0.1)], fill=land)

    elif planet_type == 'jupiter':
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                     fill=config['base'])
        bands = config['bands']
        for i in range(7):
            band_y = cy - radius + (i * 2 * radius // 7)
            for dy in range(radius // 5):
                y = band_y + dy
                dist = abs(y - cy)
                if dist < radius:
                    x_ext = int(math.sqrt(radius**2 - dist**2))
                    draw.line([(cx - x_ext, y), (cx + x_ext, y)],
                               fill=bands[i % 2], width=1)
        # Great Red Spot
        draw.ellipse([cx+int(radius*0.15), cy+int(radius*0.1),
                      cx+int(radius*0.45), cy+int(radius*0.26)],
                     fill=(180, 100, 80))

    elif planet_type == 'saturn':
        ring = config['ring']
        for i in range(3):
            rr = int(radius * (1.3 + i * 0.15))
            draw.arc([cx-rr, cy-int(radius*0.2), cx+rr, cy+int(radius*0.2)],
                     0, 180, fill=ring, width=max(1, 8-i*2))
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                     fill=config['base'])
        for i in range(3):
            rr = int(radius * (1.3 + i * 0.15))
            draw.arc([cx-rr, cy-int(radius*0.2), cx+rr, cy+int(radius*0.2)],
                     180, 360, fill=ring, width=max(1, 8-i*2))

    elif planet_type == 'black_hole':
        for i in range(5, 0, -1):
            r = int(radius * (1.2 + i * 0.1))
            draw.ellipse([cx-r, cy-int(r*0.3), cx+r, cy+int(r*0.3)],
                         fill=(80+i*15, 30+i*10, 120+i*10))
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                     fill=(5, 5, 5))

    elif planet_type == 'neutron_star':
        for i in range(6, 0, -1):
            r = radius + i * int(radius * 0.1)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r],
                         fill=(150+i*15, 150+i*15, 255))
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                     fill=config['base'])

    elif planet_type == 'moon':
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                     fill=config['base'])
        craters = [(0.3, -0.2, 0.15), (-0.2, 0.3, 0.12),
                   (0.4, 0.2, 0.1), (-0.3, -0.3, 0.08)]
        for dx, dy, size in craters:
            cr = int(size * radius)
            draw.ellipse([cx+int(dx*radius)-cr, cy+int(dy*radius)-cr,
                          cx+int(dx*radius)+cr, cy+int(dy*radius)+cr],
                         fill=config.get('crater', (140, 140, 140)))
    else:
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                     fill=config.get('base', (150, 150, 150)))

    # Highlight
    hx, hy = cx - radius//3, cy - radius//3
    for r in range(radius//4, 0, -2):
        draw.ellipse([hx-r, hy-r, hx+r, hy+r],
                     fill=(255, 255, 255) if r > radius//8 else (220, 220, 255))

    _draw_eyes(draw, cx, cy, radius, expression, planet_type)


def _draw_eyes(draw, cx, cy, radius, expression='neutral', planet_type='earth'):
    expressions = {
        'neutral':      {'scale': 1.0, 'pupil_offset': (0, 0)},
        'happy':        {'scale': 1.0, 'happy': True},
        'scared':       {'scale': 1.5, 'small_pupil': True},
        'shocked':      {'scale': 1.7, 'small_pupil': True},
        'excited':      {'scale': 1.3},
        'thinking':     {'scale': 1.0, 'pupil_offset': (0.2, -0.2)},
        'angry':        {'scale': 0.9, 'angry': True},
        'smug':         {'scale': 0.85, 'pupil_offset': (0.15, 0.1)},
        'looking_left': {'scale': 1.0, 'pupil_offset': (-0.35, 0)},
        'looking_right':{'scale': 1.0, 'pupil_offset': (0.35, 0)},
        'sleeping':     {'scale': 1.0, 'closed': True},
        'dead':         {'scale': 1.2, 'x_eyes': True},
    }
    expr = expressions.get(expression, expressions['neutral'])
    eye_scale = expr.get('scale', 1.0)
    spacing = radius * 0.32
    eye_y = int(cy - radius * 0.08)
    eye_r = int(radius * 0.18 * eye_scale)
    pupil_r = int(eye_r * (0.35 if expr.get('small_pupil') else 0.5))
    eye_white = (255, 255, 220) if planet_type == 'sun' else (255, 255, 255)

    for i, ex in enumerate([int(cx - spacing), int(cx + spacing)]):
        if expr.get('happy'):
            draw.arc([ex-eye_r, eye_y-eye_r, ex+eye_r, eye_y+eye_r],
                     200, 340, fill=(0, 0, 0), width=max(4, eye_r//3))
        elif expr.get('closed'):
            draw.line([(ex-eye_r, eye_y), (ex+eye_r, eye_y)],
                      fill=(0, 0, 0), width=4)
        elif expr.get('x_eyes'):
            draw.line([(ex-eye_r, eye_y-eye_r), (ex+eye_r, eye_y+eye_r)],
                      fill=(0, 0, 0), width=4)
            draw.line([(ex-eye_r, eye_y+eye_r), (ex+eye_r, eye_y-eye_r)],
                      fill=(0, 0, 0), width=4)
        elif expr.get('angry'):
            draw.ellipse([ex-eye_r, eye_y-eye_r, ex+eye_r, eye_y+eye_r],
                         fill=eye_white, outline=(0, 0, 0), width=2)
            if i == 0:
                draw.line([(ex-eye_r-5, eye_y-eye_r+5),
                            (ex+eye_r+5, eye_y-eye_r-8)],
                           fill=(0, 0, 0), width=5)
            else:
                draw.line([(ex-eye_r-5, eye_y-eye_r-8),
                            (ex+eye_r+5, eye_y-eye_r+5)],
                           fill=(0, 0, 0), width=5)
            offset = expr.get('pupil_offset', (0, 0.1))
            px = ex + int(offset[0] * eye_r)
            py = eye_y + int(offset[1] * eye_r)
            draw.ellipse([px-pupil_r, py-pupil_r, px+pupil_r, py+pupil_r],
                         fill=(0, 0, 0))
        else:
            draw.ellipse([ex-eye_r, eye_y-eye_r, ex+eye_r, eye_y+eye_r],
                         fill=eye_white, outline=(0, 0, 0), width=2)
            offset = expr.get('pupil_offset', (0, 0))
            px = ex + int(offset[0] * eye_r)
            py = eye_y + int(offset[1] * eye_r)
            draw.ellipse([px-pupil_r, py-pupil_r, px+pupil_r, py+pupil_r],
                         fill=(0, 0, 0))
            hl_r = max(3, pupil_r // 2)
            draw.ellipse([px-int(pupil_r*0.4)-hl_r, py-int(pupil_r*0.4)-hl_r,
                           px-int(pupil_r*0.4)+hl_r, py-int(pupil_r*0.4)+hl_r],
                         fill=(255, 255, 255))

# =============================================================================
# ENTRY ANIMATIONS
# =============================================================================
def apply_entry_animation(progress, anim_type, duration=0.3):
    if anim_type == 'none' or progress > duration:
        return {'scale': 1.0, 'offset': (0, 0), 'alpha': 1.0}
    t = min(progress / duration, 1.0)
    if anim_type == 'pop_in':
        return {'scale': ease_out_back(t), 'offset': (0, 0), 'alpha': 1.0}
    elif anim_type == 'slide_from_left':
        return {'scale': 1.0, 'offset': (-WIDTH * (1 - ease_out_cubic(t)), 0), 'alpha': 1.0}
    elif anim_type == 'slide_from_right':
        return {'scale': 1.0, 'offset': (WIDTH * (1 - ease_out_cubic(t)), 0), 'alpha': 1.0}
    elif anim_type == 'slide_from_top':
        return {'scale': 1.0, 'offset': (0, -HEIGHT * (1 - ease_out_cubic(t))), 'alpha': 1.0}
    elif anim_type == 'slide_from_bottom':
        return {'scale': 1.0, 'offset': (0, HEIGHT * (1 - ease_out_cubic(t))), 'alpha': 1.0}
    elif anim_type == 'fade_in':
        return {'scale': 1.0, 'offset': (0, 0), 'alpha': t}
    elif anim_type == 'zoom_in':
        return {'scale': 0.3 + 0.7 * ease_out_cubic(t), 'offset': (0, 0), 'alpha': t}
    elif anim_type == 'bounce_in':
        return {'scale': ease_out_elastic(t), 'offset': (0, 0), 'alpha': 1.0}
    return {'scale': 1.0, 'offset': (0, 0), 'alpha': 1.0}

def apply_object_effect(frame_num, effect_type):
    t = frame_num / FPS
    if effect_type == 'idle_bounce':
        return {'offset': (0, math.sin(t * 2) * 8)}
    elif effect_type == 'shake':
        random.seed(frame_num)
        return {'offset': (random.randint(-10, 10), random.randint(-10, 10))}
    elif effect_type == 'pulse':
        return {'scale_mod': 1.0 + math.sin(t * 4) * 0.05}
    elif effect_type == 'glow':
        return {'glow': 0.5 + math.sin(t * 3) * 0.3}
    elif effect_type == 'wobble':
        return {'rotation': math.sin(t * 3) * 10}
    elif effect_type == 'vibrate':
        random.seed(frame_num)
        return {'offset': (random.randint(-4, 4), random.randint(-4, 4))}
    elif effect_type == 'float':
        return {'offset': (0, math.sin(t * 1.5) * 15)}
    elif effect_type == 'spin':
        return {'rotation': (t * 90) % 360}
    return {}

# =============================================================================
# SCREEN EFFECTS
# =============================================================================
def apply_screen_effect(img, effect_type, frame_num=0):
    if effect_type == 'camera_shake':
        random.seed(frame_num)
        dx, dy = random.randint(-12, 12), random.randint(-12, 12)
        result = Image.new('RGB', img.size, COLORS['background'])
        result.paste(img, (dx, dy))
        return result
    elif effect_type == 'flash':
        flash = Image.new('RGB', img.size, (255, 255, 255))
        return Image.blend(img, flash, 0.35)
    elif effect_type == 'chromatic_aberration':
        r, g, b = img.split()
        r = r.transform(img.size, Image.AFFINE, (1, 0, -4, 0, 1, 0))
        b = b.transform(img.size, Image.AFFINE, (1, 0, 4, 0, 1, 0))
        return Image.merge('RGB', (r, g, b))
    elif effect_type == 'vignette_pulse':
        vignette = Image.new('L', img.size, 255)
        draw = ImageDraw.Draw(vignette)
        cx, cy = img.width // 2, img.height // 2
        max_r = max(cx, cy) * 1.5
        for r in range(int(max_r), 0, -10):
            draw.ellipse([cx-r, cy-r, cx+r, cy+r],
                         fill=int(255 * (r / max_r)))
        pulse = 0.25 + math.sin(frame_num / FPS * 4) * 0.1
        vignette = ImageEnhance.Brightness(vignette).enhance(1 - pulse)
        result = img.copy().convert('RGBA')
        result.putalpha(vignette)
        bg = Image.new('RGBA', img.size, (*COLORS['background'], 255))
        return Image.alpha_composite(bg, result).convert('RGB')
    elif effect_type == 'glitch':
        result = img.copy()
        if random.random() < 0.4:
            y = random.randint(0, img.height - 40)
            h = random.randint(15, 40)
            sl = img.crop((0, y, img.width, y + h))
            result.paste(sl, (random.randint(-25, 25), y))
        return result
    return img

# =============================================================================
# TEXT RENDERING  (enhanced: number highlighting, glow, word-by-word)
# =============================================================================
def render_text_enhanced(img, text_config, progress, frame_num, theme_key="default"):
    """
    Full-featured text renderer:
    - word_by_word: reveals words progressively
    - slam_in: big then normal
    - typewriter: char by char
    - Numbers auto-highlighted yellow + slightly larger
    - Planet names auto-highlighted cyan
    - Glow behind all text
    """
    content = text_config.get('content', '')
    if not content:
        return img

    position = text_config.get('position', 'top')
    style = text_config.get('style', 'word_by_word')
    highlight = text_config.get('highlight', [])  # optional extra highlight words

    base_font_size = 52
    theme = THEMES.get(theme_key, THEMES["default"])
    accent = theme["accent"]

    # Apply style
    if style == 'word_by_word':
        words = content.split()
        num_show = max(1, int(len(words) * min(progress * 1.4, 1.0)))
        content = ' '.join(words[:num_show])
    elif style == 'slam_in':
        if progress < 0.15:
            base_font_size = int(52 * (3.0 - 2.0 * (progress / 0.15)))
            base_font_size = max(52, min(base_font_size, 130))
    elif style == 'typewriter':
        num_chars = int(len(content) * min(progress * 1.2, 1.0))
        content = content[:num_chars]

    result = img.convert('RGBA')
    font = get_font(base_font_size)

    y_base = 170 if position == 'top' else HEIGHT - 320

    # Word-level rendering with color coding
    lines = textwrap.wrap(content, width=22)
    line_height = int(base_font_size * 1.35)

    for li, line in enumerate(lines):
        ly = y_base + li * line_height
        words_in_line = line.split()

        # Measure total line width for centering
        total_w = 0
        temp_draw = ImageDraw.Draw(result)
        for w in words_in_line:
            bb = temp_draw.textbbox((0, 0), w + ' ', font=font)
            total_w += bb[2] - bb[0]
        lx = max(40, (WIDTH - total_w) // 2)

        for word in words_in_line:
            word_clean = word.lower().strip('.,!?:')

            # Determine color and size
            is_number = any(c.isdigit() for c in word)
            is_planet = word_clean in ['earth', 'mars', 'jupiter', 'saturn',
                                        'sun', 'moon', 'neptune', 'venus',
                                        'mercury', 'uranus']
            is_highlight = word_clean in [h.lower() for h in highlight]
            is_caps = word.isupper() and len(word) > 2

            if is_number:
                color = COLORS['text_yellow']
                glow_col = COLORS['glow_yellow']
                word_font = get_font(int(base_font_size * 1.18))
            elif is_planet:
                color = COLORS['text_cyan']
                glow_col = COLORS['glow_blue']
                word_font = font
            elif is_highlight or is_caps:
                color = tuple(accent)
                glow_col = tuple(accent)
                word_font = get_font(int(base_font_size * 1.1))
            else:
                color = COLORS['text_white']
                glow_col = COLORS['glow_blue']
                word_font = font

            # Glow
            glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_layer)
            for off in [6, 4, 2]:
                a = int(45 * (1 - off / 7))
                for dx in range(-off, off+1, 2):
                    for dy in range(-off, off+1, 2):
                        gd.text((lx+dx, ly+dy), word, font=word_font,
                                 fill=(*glow_col, a))
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(2))
            result = Image.alpha_composite(result, glow_layer)

            # Outline
            ol = Image.new('RGBA', img.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(ol)
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    od.text((lx+dx, ly+dy), word, font=word_font,
                             fill=(0, 0, 0, 255))
            result = Image.alpha_composite(result, ol)

            # Text
            tl = Image.new('RGBA', img.size, (0, 0, 0, 0))
            td = ImageDraw.Draw(tl)
            td.text((lx, ly), word, font=word_font, fill=(*color, 255))
            result = Image.alpha_composite(result, tl)

            bb = ImageDraw.Draw(result).textbbox((0, 0), word + ' ', font=word_font)
            lx += bb[2] - bb[0]

    return result.convert('RGB')

# =============================================================================
# MAIN FRAME RENDERER
# =============================================================================
def render_frame(scene, frame_num, total_frames, parallax_layers,
                  shooting_star_t, theme_key, video_start_frame, total_video_frames):
    progress = frame_num / max(total_frames - 1, 1)
    t = frame_num / FPS
    total_dur = total_frames / FPS

    # Composite parallax background
    frame = composite_parallax(parallax_layers, t, total_dur, shooting_star_t)

    draw = ImageDraw.Draw(frame)
    layers = scene.get('layers', [])
    text_config = scene.get('text', {})
    screen_effects = scene.get('screen_effects', [])

    # Draw glow rings under planets (separate RGBA layer)
    theme = THEMES.get(theme_key, THEMES["default"])
    glow_colors = {
        'earth': (60, 140, 255), 'mars': (255, 100, 60),
        'jupiter': (255, 180, 120), 'saturn': (220, 200, 150),
        'sun': (255, 200, 50), 'moon': (200, 200, 220),
        'neptune': (80, 140, 255), 'venus': (255, 200, 120),
        'black_hole': (180, 60, 255), 'neutron_star': (180, 180, 255),
    }

    for layer in layers:
        if layer.get('type') != 'planet':
            continue
        name = layer.get('name', 'earth')
        position = layer.get('position', 'center')
        size_key = layer.get('size', 'medium')
        expression = layer.get('expression', 'neutral')
        entry_anim = layer.get('entry_animation', 'pop_in')
        effects = layer.get('effects', [])

        pos_norm = POSITIONS.get(position, (0.5, 0.5))
        cx = int(pos_norm[0] * WIDTH)
        cy = int(pos_norm[1] * HEIGHT)
        radius = SIZES.get(size_key, 150)

        entry = apply_entry_animation(progress, entry_anim)
        radius = int(radius * entry.get('scale', 1.0))
        cx += int(entry.get('offset', (0, 0))[0])
        cy += int(entry.get('offset', (0, 0))[1])

        for effect in effects:
            eff = apply_object_effect(frame_num, effect)
            if 'offset' in eff:
                cx += int(eff['offset'][0])
                cy += int(eff['offset'][1])
            if 'scale_mod' in eff:
                radius = int(radius * eff['scale_mod'])

        if radius < 10:
            continue

        # Glow ring layer
        glow_col = glow_colors.get(name, (150, 150, 255))
        pulse = 1.0 + 0.04 * math.sin(frame_num / FPS * 2 * math.pi * 0.8)
        glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        for i in range(7, 0, -1):
            r = int(radius * (1.12 + i * 0.07) * pulse)
            a = int(28 * (1 - i / 8))
            gd.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(*glow_col, a))
        frame = Image.alpha_composite(frame.convert("RGBA"),
                                       glow_layer).convert("RGB")
        draw = ImageDraw.Draw(frame)

        # Planet body + eyes
        draw_planet_with_glow(draw, cx, cy, radius, name, expression, frame_num)

    # Text
    if text_config:
        frame = render_text_enhanced(frame, text_config, progress,
                                      frame_num, theme_key)

    # Screen effects
    for effect in screen_effects:
        frame = apply_screen_effect(frame, effect, frame_num)

    # Progress bar (global video progress)
    global_progress = (video_start_frame + frame_num) / max(total_video_frames, 1)
    draw_progress_bar(frame, global_progress, theme_key)

    return np.array(frame)

# =============================================================================
# VIDEO CREATION
# =============================================================================
def create_video(script_data, output_path):
    print(f"🎬 Cinema renderer starting: {output_path}")

    timeline = script_data.get('timeline', [])
    if not timeline:
        print("❌ No timeline in script")
        return False

    idea = script_data.get('idea', {})
    topic_family = idea.get('topic_family', 'default')
    theme_key = topic_family if topic_family in THEMES else 'default'
    hook_text = idea.get('hook', '')

    print(f"🎨 Theme: {theme_key}")
    print(f"🎣 Hook: {hook_text[:60]}")

    # Fetch NASA background (optional)
    nasa_bg = fetch_nasa_background(idea.get('topic', ''))

    # Build parallax layers
    parallax_layers = create_parallax_starfield(theme_key, seed=42, nasa_bg=nasa_bg)

    # Pick shooting star timing (random within video)
    total_script_duration = sum(
        s.get('time_end', 4) - s.get('time_start', 0) for s in timeline
    )
    hook_dur = 2.5 if hook_text else 0
    total_duration = hook_dur + total_script_duration
    shooting_star_t = random.uniform(total_duration * 0.3, total_duration * 0.75)

    total_video_frames = int(total_duration * FPS)
    clips = []
    current_frame_offset = 0

    # 1. Hook screen clip
    if hook_text:
        hook_duration = 2.5
        hook_total_frames = int(hook_duration * FPS)
        print("⚡ Rendering hook screen...")

        def make_hook_frame(t,
                             _layers=parallax_layers,
                             _hook=hook_text,
                             _theme=theme_key,
                             _dur=hook_duration,
                             _ss_t=shooting_star_t):
            return render_hook_screen(_hook, _theme, _layers, t, _dur)

        clips.append(VideoClip(make_hook_frame, duration=hook_duration))
        current_frame_offset += hook_total_frames

    # 2. Main scene clips
    for i, scene in enumerate(timeline):
        start = scene.get('time_start', 0)
        end = scene.get('time_end', 4)
        duration = max(0.5, end - start)
        total_frames = int(duration * FPS)
        text_preview = scene.get('text', {}).get('content', '')[:40]
        print(f"  🎬 Scene {i+1}/{len(timeline)} ({duration:.1f}s): {text_preview}...")

        frame_offset = current_frame_offset

        def make_frame(t,
                        _scene=scene,
                        _total=total_frames,
                        _layers=parallax_layers,
                        _ss=shooting_star_t,
                        _theme=theme_key,
                        _offset=frame_offset,
                        _total_v=total_video_frames):
            fn = min(int(t * FPS), _total - 1)
            return render_frame(_scene, fn, _total, _layers,
                                  _ss, _theme, _offset, _total_v)

        clips.append(VideoClip(make_frame, duration=duration))
        current_frame_offset += total_frames

    # Join
    print("🔗 Joining clips...")
    video = concatenate_videoclips(clips, method="compose")

    # Audio
    audio_added = False
    if os.path.exists(AUDIO_DIR):
        audio_files = [f for f in os.listdir(AUDIO_DIR)
                       if f.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a'))]
        # Try theme-matched music first
        matched = [f for f in audio_files if theme_key in f.lower()]
        if not matched:
            matched = audio_files
        if matched:
            try:
                music_path = os.path.join(AUDIO_DIR, random.choice(matched))
                audio = AudioFileClip(music_path)
                if audio.duration < video.duration:
                    loops = int(video.duration / audio.duration) + 1
                    audio = concatenate_videoclips  # won't hit, just safety
                    from moviepy.editor import concatenate_audioclips
                    audio = concatenate_audioclips(
                        [AudioFileClip(music_path)] * (int(video.duration / AudioFileClip(music_path).duration) + 1)
                    )
                audio = audio.subclip(0, video.duration).volumex(0.28)
                audio = audio.audio_fadein(0.8).audio_fadeout(1.5)
                video = video.set_audio(audio)
                print(f"🎵 Music: {os.path.basename(music_path)}")
                audio_added = True
            except Exception as e:
                print(f"⚠️ Music error: {e}")

    if not audio_added:
        print("⚠️ No audio added")

    # Export
    print(f"💾 Encoding → {output_path}")
    video.write_videofile(
        output_path,
        fps=FPS,
        codec='libx264',
        preset='medium',
        threads=4,
        logger=None,
        bitrate='6000k',
    )

    # Cleanup
    try:
        if video.audio:
            video.audio.close()
        video.close()
        for c in clips:
            c.close()
    except Exception:
        pass

    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"✅ Done! {size_mb:.1f} MB → {output_path}")
        return True

    print("❌ Output file not created")
    return False

# =============================================================================
# ENTRY POINT
# =============================================================================
def process_scripts():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(SCRIPTS_DIR):
        print(f"📁 No scripts directory: {SCRIPTS_DIR}")
        return
    scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.json')]
    if not scripts:
        print("📭 No scripts to process")
        return
    print(f"📁 {len(scripts)} script(s) found")

    for script_file in scripts:
        script_path = os.path.join(SCRIPTS_DIR, script_file)
        try:
            with open(script_path, 'r') as f:
                script_data = json.load(f)
            if script_data.get('rendered'):
                print(f"⏭️  Already rendered: {script_file}")
                continue
            output_path = os.path.join(
                OUTPUT_DIR, script_file.replace('.json', '.mp4')
            )
            if create_video(script_data, output_path):
                script_data['rendered'] = True
                script_data['rendered_at'] = datetime.now().isoformat()
                script_data['video_path'] = output_path
                with open(script_path, 'w') as f:
                    json.dump(script_data, f, indent=2)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

def main():
    print("=" * 60)
    print("🎬 ASTRO SHORTS V2 — Cinema Renderer")
    print("=" * 60)
    process_scripts()
    print("=" * 60)
    print("✅ Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
