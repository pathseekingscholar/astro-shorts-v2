"""
Video Renderer V2 - UPGRADED VERSION
Inspired by "Beyond Observable Universe" style:
- Cartoon planets with expressive eyes
- Glow/neon text effects
- Word-by-word text animation
- Color-coded keywords
- Shake effects on dramatic moments
- Layered sound effects (whoosh, pop, reveal)
"""

import os
import json
import random
import math
from datetime import datetime

# MoviePy imports
from moviepy.editor import (
    VideoClip, AudioFileClip, CompositeVideoClip, 
    CompositeAudioClip, concatenate_videoclips, ColorClip
)
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import numpy as np

# =============================================================================
# CONFIGURATION
# =============================================================================
WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION_PER_SCENE = 4  # seconds

# Directories
SCRIPTS_DIR = "scripts_output"
OUTPUT_DIR = "videos_output"
AUDIO_DIR = "assets/audio"
SFX_DIR = "assets/sfx"

# Colors (matching the "Beyond Observable Universe" style)
COLORS = {
    'background': (10, 10, 30),
    'text_primary': (255, 255, 255),
    'text_highlight': (0, 255, 255),      # Cyan
    'text_action': (255, 100, 100),       # Red for action words
    'text_number': (255, 255, 0),         # Yellow for numbers
    'glow_primary': (0, 200, 255),        # Blue glow
    'glow_secondary': (255, 100, 200),    # Pink glow
}

# Action words to highlight in red
ACTION_WORDS = [
    'boom', 'crash', 'destroy', 'explode', 'die', 'kill', 'burn', 
    'crush', 'smash', 'gone', 'dead', 'massive', 'huge', 'giant',
    'impossible', 'insane', 'crazy', 'extreme', 'deadly', 'dangerous'
]

# Planet configurations with personality
PLANETS = {
    'earth': {
        'base_color': (100, 149, 237),
        'accent_color': (34, 139, 34),
        'has_continents': True,
        'default_expression': 'happy'
    },
    'mars': {
        'base_color': (205, 92, 92),
        'accent_color': (139, 69, 19),
        'has_continents': False,
        'default_expression': 'neutral'
    },
    'jupiter': {
        'base_color': (218, 165, 105),
        'accent_color': (160, 82, 45),
        'has_bands': True,
        'default_expression': 'smug'
    },
    'saturn': {
        'base_color': (210, 180, 140),
        'accent_color': (238, 232, 170),
        'has_rings': True,
        'default_expression': 'neutral'
    },
    'venus': {
        'base_color': (255, 198, 73),
        'accent_color': (255, 165, 0),
        'default_expression': 'angry'
    },
    'sun': {
        'base_color': (255, 200, 50),
        'accent_color': (255, 100, 0),
        'is_star': True,
        'default_expression': 'happy'
    },
    'moon': {
        'base_color': (200, 200, 200),
        'accent_color': (150, 150, 150),
        'has_craters': True,
        'default_expression': 'neutral'
    },
    'black_hole': {
        'base_color': (20, 20, 20),
        'accent_color': (50, 0, 80),
        'is_black_hole': True,
        'default_expression': 'evil'
    }
}

# Eye expressions
EXPRESSIONS = {
    'neutral': {'eye_size': 1.0, 'pupil_pos': (0, 0), 'eye_shape': 'round'},
    'happy': {'eye_size': 1.0, 'pupil_pos': (0, 0), 'eye_shape': 'happy'},
    'scared': {'eye_size': 1.4, 'pupil_pos': (0, 0), 'eye_shape': 'round', 'pupil_small': True},
    'shocked': {'eye_size': 1.6, 'pupil_pos': (0, 0), 'eye_shape': 'round', 'pupil_small': True},
    'angry': {'eye_size': 0.9, 'pupil_pos': (0, 0.1), 'eye_shape': 'angry'},
    'smug': {'eye_size': 0.8, 'pupil_pos': (0.1, 0.1), 'eye_shape': 'smug'},
    'evil': {'eye_size': 0.9, 'pupil_pos': (0, 0), 'eye_shape': 'evil'},
    'looking_left': {'eye_size': 1.0, 'pupil_pos': (-0.3, 0), 'eye_shape': 'round'},
    'looking_right': {'eye_size': 1.0, 'pupil_pos': (0.3, 0), 'eye_shape': 'round'},
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def ensure_dirs():
    """Create necessary directories."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SFX_DIR, exist_ok=True)


def get_font(size, bold=False):
    """Get a font, with fallbacks."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    return ImageFont.load_default()


# =============================================================================
# STARFIELD GENERATOR (Enhanced)
# =============================================================================
def create_starfield(width, height, num_stars=200, seed=None):
    """Create a layered starfield with depth."""
    if seed:
        random.seed(seed)
    
    img = Image.new('RGB', (width, height), COLORS['background'])
    draw = ImageDraw.Draw(img)
    
    # Layer 1: Distant small stars (dim)
    for _ in range(num_stars):
        x = random.randint(0, width)
        y = random.randint(0, height)
        brightness = random.randint(30, 80)
        size = 1
        draw.ellipse([x, y, x+size, y+size], fill=(brightness, brightness, brightness+20))
    
    # Layer 2: Medium stars
    for _ in range(num_stars // 3):
        x = random.randint(0, width)
        y = random.randint(0, height)
        brightness = random.randint(100, 180)
        size = random.randint(1, 2)
        draw.ellipse([x, y, x+size, y+size], fill=(brightness, brightness, brightness))
    
    # Layer 3: Bright stars with glow
    for _ in range(num_stars // 10):
        x = random.randint(0, width)
        y = random.randint(0, height)
        # Glow
        for r in range(6, 0, -1):
            alpha = int(30 * (1 - r/6))
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(100+alpha, 100+alpha, 150+alpha))
        # Core
        draw.ellipse([x-1, y-1, x+1, y+1], fill=(255, 255, 255))
    
    # Add subtle nebula tint
    nebula_colors = [
        (30, 10, 50),   # Purple
        (10, 30, 50),   # Blue
        (50, 20, 30),   # Red
    ]
    nebula_color = random.choice(nebula_colors)
    
    # Create nebula overlay
    nebula = Image.new('RGB', (width, height), nebula_color)
    img = Image.blend(img, nebula, 0.15)
    
    return img


# =============================================================================
# CARTOON PLANET GENERATOR
# =============================================================================
def draw_cartoon_planet(draw, cx, cy, radius, planet_type='earth', expression='neutral'):
    """Draw a cartoon planet with expressive eyes."""
    
    config = PLANETS.get(planet_type, PLANETS['earth'])
    expr = EXPRESSIONS.get(expression, EXPRESSIONS['neutral'])
    
    base_color = config['base_color']
    accent_color = config['accent_color']
    
    # Draw planet body
    if config.get('is_black_hole'):
        # Black hole with accretion disk
        for r in range(int(radius * 1.5), int(radius * 0.8), -2):
            alpha = int(100 * (1 - (r - radius * 0.8) / (radius * 0.7)))
            color = (50 + alpha // 3, 0, 80 + alpha // 2)
            draw.ellipse([cx-r, cy-r//3, cx+r, cy+r//3], fill=color)
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=(5, 5, 5))
    
    elif config.get('is_star'):
        # Sun with glow
        for r in range(int(radius * 1.4), radius, -3):
            glow_intensity = int(150 * (1 - (r - radius) / (radius * 0.4)))
            glow_color = (255, 200 + glow_intensity // 4, glow_intensity)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=glow_color)
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=base_color)
    
    else:
        # Regular planet
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=base_color)
        
        # Add features
        if config.get('has_continents'):
            # Draw simple continent shapes
            for _ in range(3):
                cont_x = cx + random.randint(-radius//2, radius//2)
                cont_y = cy + random.randint(-radius//2, radius//2)
                cont_size = random.randint(radius//6, radius//3)
                draw.ellipse([cont_x-cont_size, cont_y-cont_size//2, 
                            cont_x+cont_size, cont_y+cont_size//2], fill=accent_color)
        
        if config.get('has_bands'):
            # Jupiter-style bands
            for i in range(-3, 4):
                band_y = cy + i * radius // 4
                band_color = accent_color if i % 2 == 0 else base_color
                draw.rectangle([cx-radius, band_y-radius//10, cx+radius, band_y+radius//10], 
                             fill=band_color)
            # Redraw circle outline to clean up edges
            draw.ellipse([cx-radius-2, cy-radius-2, cx+radius+2, cy+radius+2], 
                        outline=base_color, width=4)
        
        if config.get('has_rings'):
            # Saturn rings - draw behind first, then planet, then rings in front
            ring_width = int(radius * 0.3)
            for i in range(3):
                r = radius + ring_width // 2 + i * (ring_width // 3)
                ring_color = (200 - i*20, 180 - i*20, 150 - i*20)
                draw.arc([cx-int(r*1.5), cy-r//3, cx+int(r*1.5), cy+r//3], 
                        200, 340, fill=ring_color, width=8)
        
        if config.get('has_craters'):
            # Moon craters
            for _ in range(5):
                crater_x = cx + random.randint(-radius//2, radius//2)
                crater_y = cy + random.randint(-radius//2, radius//2)
                crater_size = random.randint(radius//10, radius//5)
                draw.ellipse([crater_x-crater_size, crater_y-crater_size,
                            crater_x+crater_size, crater_y+crater_size], 
                           fill=accent_color)
    
    # Draw eyes (unless it's a black hole)
    if not config.get('is_black_hole'):
        draw_eyes(draw, cx, cy, radius, expr, config)


def draw_eyes(draw, cx, cy, radius, expr, planet_config):
    """Draw expressive cartoon eyes on a planet."""
    
    eye_size_mult = expr.get('eye_size', 1.0)
    pupil_offset = expr.get('pupil_pos', (0, 0))
    eye_shape = expr.get('eye_shape', 'round')
    pupil_small = expr.get('pupil_small', False)
    
    # Eye positioning
    eye_spacing = radius * 0.35
    eye_y = cy - radius * 0.05
    eye_radius = int(radius * 0.18 * eye_size_mult)
    pupil_radius = int(eye_radius * (0.35 if pupil_small else 0.55))
    
    left_eye_x = cx - eye_spacing
    right_eye_x = cx + eye_spacing
    
    for eye_x in [left_eye_x, right_eye_x]:
        # Eye white
        if eye_shape == 'happy':
            # Happy curved eyes (like ^_^)
            draw.arc([eye_x - eye_radius, eye_y - eye_radius, 
                     eye_x + eye_radius, eye_y + eye_radius],
                    200, 340, fill=(0, 0, 0), width=max(3, eye_radius // 4))
        elif eye_shape == 'angry':
            # Angry eyes with angled top
            draw.ellipse([eye_x - eye_radius, eye_y - eye_radius,
                         eye_x + eye_radius, eye_y + eye_radius], fill=(255, 255, 255))
            # Angry eyebrow line
            brow_color = planet_config.get('base_color', (100, 100, 100))
            if eye_x < cx:  # Left eye
                draw.polygon([(eye_x - eye_radius - 5, eye_y - eye_radius + 5),
                            (eye_x + eye_radius + 5, eye_y - eye_radius // 2),
                            (eye_x + eye_radius + 5, eye_y - eye_radius - 5),
                            (eye_x - eye_radius - 5, eye_y - eye_radius - 5)], 
                           fill=brow_color)
            else:  # Right eye
                draw.polygon([(eye_x + eye_radius + 5, eye_y - eye_radius + 5),
                            (eye_x - eye_radius - 5, eye_y - eye_radius // 2),
                            (eye_x - eye_radius - 5, eye_y - eye_radius - 5),
                            (eye_x + eye_radius + 5, eye_y - eye_radius - 5)],
                           fill=brow_color)
            # Pupil
            px = eye_x + int(pupil_offset[0] * eye_radius)
            py = eye_y + int(pupil_offset[1] * eye_radius)
            draw.ellipse([px - pupil_radius, py - pupil_radius,
                         px + pupil_radius, py + pupil_radius], fill=(0, 0, 0))
        elif eye_shape == 'evil':
            # Evil narrow eyes with red
            draw.ellipse([eye_x - eye_radius, eye_y - eye_radius // 2,
                         eye_x + eye_radius, eye_y + eye_radius // 2], fill=(255, 50, 50))
            # Slit pupil
            draw.ellipse([eye_x - pupil_radius // 3, eye_y - pupil_radius,
                         eye_x + pupil_radius // 3, eye_y + pupil_radius], fill=(0, 0, 0))
        elif eye_shape == 'smug':
            # Smug half-closed eyes
            draw.ellipse([eye_x - eye_radius, eye_y - eye_radius // 2,
                         eye_x + eye_radius, eye_y + eye_radius], fill=(255, 255, 255))
            px = eye_x + int(pupil_offset[0] * eye_radius)
            py = eye_y + int(pupil_offset[1] * eye_radius) + eye_radius // 4
            draw.ellipse([px - pupil_radius, py - pupil_radius,
                         px + pupil_radius, py + pupil_radius], fill=(0, 0, 0))
            # Highlight
            hl_r = max(2, pupil_radius // 3)
            draw.ellipse([px - pupil_radius//2 - hl_r, py - pupil_radius//2 - hl_r,
                         px - pupil_radius//2 + hl_r, py - pupil_radius//2 + hl_r], 
                        fill=(255, 255, 255))
        else:
            # Normal round eyes
            draw.ellipse([eye_x - eye_radius, eye_y - eye_radius,
                         eye_x + eye_radius, eye_y + eye_radius], fill=(255, 255, 255))
            # Pupil with offset
            px = eye_x + int(pupil_offset[0] * eye_radius)
            py = eye_y + int(pupil_offset[1] * eye_radius)
            draw.ellipse([px - pupil_radius, py - pupil_radius,
                         px + pupil_radius, py + pupil_radius], fill=(0, 0, 0))
            # Highlight
            hl_r = max(2, pupil_radius // 3)
            draw.ellipse([px - pupil_radius//2 - hl_r, py - pupil_radius//2 - hl_r,
                         px - pupil_radius//2 + hl_r, py - pupil_radius//2 + hl_r], 
                        fill=(255, 255, 255))


# =============================================================================
# TEXT RENDERING WITH GLOW
# =============================================================================
def render_text_with_glow(img, text, x, y, font_size=60, 
                          text_color=(255, 255, 255), 
                          glow_color=(0, 200, 255),
                          glow_radius=6):
    """Render text with neon glow effect at specific position."""
    
    font = get_font(font_size, bold=True)
    
    # Create layers
    glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    
    # Draw glow
    for offset in range(glow_radius, 0, -1):
        alpha = int(80 * (1 - offset / glow_radius))
        glow_rgba = (*glow_color, alpha)
        for dx in range(-offset, offset + 1):
            for dy in range(-offset, offset + 1):
                if dx*dx + dy*dy <= offset*offset:
                    glow_draw.text((x + dx, y + dy), text, font=font, fill=glow_rgba)
    
    # Blur glow
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=2))
    
    # Draw outline
    outline_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    outline_draw = ImageDraw.Draw(outline_layer)
    outline_width = 3
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if abs(dx) + abs(dy) <= outline_width + 1:
                outline_draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 255))
    
    # Draw main text
    text_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text((x, y), text, font=font, fill=(*text_color, 255))
    
    # Composite
    result = img.convert('RGBA')
    result = Image.alpha_composite(result, glow_layer)
    result = Image.alpha_composite(result, outline_layer)
    result = Image.alpha_composite(result, text_layer)
    
    return result.convert('RGB')


def get_word_color(word):
    """Determine what color a word should be."""
    word_lower = word.lower().strip('.,!?:;')
    
    # Action words in red
    if any(action in word_lower for action in ACTION_WORDS):
        return COLORS['text_action'], (255, 50, 50)
    
    # Numbers in yellow
    if any(c.isdigit() for c in word):
        return COLORS['text_number'], (255, 200, 0)
    
    # Planet names in cyan
    planet_names = ['earth', 'mars', 'jupiter', 'saturn', 'venus', 'sun', 'moon', 'neptune', 'uranus', 'mercury', 'pluto']
    if word_lower in planet_names:
        return COLORS['text_highlight'], COLORS['glow_primary']
    
    # Default white
    return COLORS['text_primary'], COLORS['glow_primary']


def render_word_by_word_frame(img, text, y_position, font_size, progress):
    """Render text word by word based on progress (0.0 to 1.0)."""
    
    words = text.split()
    if not words:
        return img
    
    # Calculate how many words should be visible
    words_to_show = max(1, int(len(words) * min(progress * 1.5, 1.0)))
    words_to_show = min(words_to_show, len(words))
    
    font = get_font(font_size, bold=True)
    temp_img = Image.new('RGB', (img.width, img.height), (0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    
    # Calculate total width of visible text
    visible_text = ' '.join(words[:words_to_show])
    bbox = temp_draw.textbbox((0, 0), visible_text, font=font)
    total_width = bbox[2] - bbox[0]
    
    # Center the text
    start_x = (img.width - total_width) // 2
    current_x = start_x
    
    result = img.copy()
    
    for i, word in enumerate(words[:words_to_show]):
        # Get word color
        text_color, glow_color = get_word_color(word)
        
        # Calculate word width
        word_with_space = word + ' '
        word_bbox = temp_draw.textbbox((0, 0), word_with_space, font=font)
        word_width = word_bbox[2] - word_bbox[0]
        
        # Pop-in scale effect for newest word
        if i == words_to_show - 1:
            word_progress = (progress * len(words) * 1.5) % 1.0
            if word_progress < 0.3:
                # Scale up effect
                scale = 0.5 + word_progress * 1.7
                adjusted_font_size = int(font_size * min(scale, 1.2))
                # Adjust position for scaling
                size_diff = (adjusted_font_size - font_size) // 2
                result = render_text_with_glow(
                    result, word, 
                    current_x - size_diff, y_position - size_diff,
                    font_size=adjusted_font_size,
                    text_color=text_color,
                    glow_color=glow_color
                )
            else:
                result = render_text_with_glow(
                    result, word, current_x, y_position,
                    font_size=font_size,
                    text_color=text_color,
                    glow_color=glow_color
                )
        else:
            result = render_text_with_glow(
                result, word, current_x, y_position,
                font_size=font_size,
                text_color=text_color,
                glow_color=glow_color
            )
        
        current_x += word_width
    
    return result


# =============================================================================
# ANIMATION EFFECTS
# =============================================================================
def apply_shake(frame_img, intensity=10, frame_num=0):
    """Apply shake effect to a frame."""
    random.seed(frame_num)  # Consistent shake per frame
    
    dx = random.randint(-intensity, intensity)
    dy = random.randint(-intensity, intensity)
    
    result = Image.new('RGB', frame_img.size, COLORS['background'])
    result.paste(frame_img, (dx, dy))
    
    return result


def ease_out_back(t):
    """Back ease-out for overshoot pop effect."""
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def ease_out_cubic(t):
    """Cubic ease-out."""
    return 1 - pow(1 - t, 3)


# =============================================================================
# SCENE RENDERING
# =============================================================================
def render_scene_frame(scene, frame_num, total_frames, starfield):
    """Render a single frame of a scene."""
    
    progress = frame_num / max(total_frames - 1, 1)
    
    # Start with starfield
    frame = starfield.copy()
    draw = ImageDraw.Draw(frame)
    
    # Scene data
    text = scene.get('text', '')
    planet_type = scene.get('planet', 'earth')
    expression = scene.get('expression', 'neutral')
    is_dramatic = scene.get('dramatic', False)
    text_position = scene.get('text_position', 'top')
    planet_position = scene.get('planet_position', 'center')
    
    # Planet animation - appears with bounce in first 30%
    planet_progress = min(progress / 0.3, 1.0)
    planet_scale = ease_out_back(planet_progress) if planet_progress < 1.0 else 1.0
    
    # Planet positions
    positions = {
        'center': (WIDTH // 2, HEIGHT // 2 + 100),
        'left': (WIDTH // 3, HEIGHT // 2 + 100),
        'right': (2 * WIDTH // 3, HEIGHT // 2 + 100),
        'top': (WIDTH // 2, HEIGHT // 3),
        'bottom': (WIDTH // 2, 2 * HEIGHT // 3 + 100),
    }
    base_x, base_y = positions.get(planet_position, positions['center'])
    
    # Planet size
    base_radius = scene.get('planet_size', 180)
    radius = int(base_radius * planet_scale)
    
    # Draw planet
    if radius > 10:
        # Use consistent seed for planet features
        random.seed(hash(planet_type))
        draw_cartoon_planet(draw, base_x, base_y, radius, planet_type, expression)
        random.seed()  # Reset seed
    
    # Convert to PIL for text rendering
    frame = Image.fromarray(np.array(frame)) if isinstance(frame, np.ndarray) else frame
    
    # Text animation - starts at 15% progress
    text_progress = max(0, (progress - 0.15) / 0.7)
    
    if text and text_progress > 0:
        # Y position for text
        if text_position == 'top':
            text_y = 180
        elif text_position == 'bottom':
            text_y = HEIGHT - 350
        else:
            text_y = 200
        
        frame = render_word_by_word_frame(
            frame, text, text_y, 
            font_size=52,
            progress=text_progress
        )
    
    # Shake effect on dramatic moments (middle of scene)
    if is_dramatic and 0.35 < progress < 0.65:
        shake_intensity = int(12 * (1 - abs(progress - 0.5) / 0.15))
        shake_intensity = max(0, min(shake_intensity, 15))
        if shake_intensity > 0:
            frame = apply_shake(frame, intensity=shake_intensity, frame_num=frame_num)
    
    return np.array(frame)


def create_scene_clip(scene, duration, starfield):
    """Create a MoviePy clip for a scene."""
    
    total_frames = int(duration * FPS)
    
    def make_frame(t):
        frame_num = int(t * FPS)
        frame_num = min(frame_num, total_frames - 1)
        return render_scene_frame(scene, frame_num, total_frames, starfield)
    
    return VideoClip(make_frame, duration=duration)


# =============================================================================
# AUDIO HANDLING
# =============================================================================
def get_background_music():
    """Get a random background music track."""
    if not os.path.exists(AUDIO_DIR):
        return None
    
    audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith(('.mp3', '.wav'))]
    if not audio_files:
        return None
    
    return os.path.join(AUDIO_DIR, random.choice(audio_files))


def create_audio_mix(music_path, duration):
    """Create audio mix with background music."""
    
    if not music_path or not os.path.exists(music_path):
        return None
    
    try:
        music = AudioFileClip(music_path)
        
        # Loop if needed
        if music.duration < duration:
            from moviepy.editor import concatenate_audioclips
            loops_needed = int(duration / music.duration) + 1
            music = concatenate_audioclips([music] * loops_needed)
        
        # Trim and adjust volume
        music = music.subclip(0, duration)
        music = music.volumex(0.25)
        
        # Fade in/out
        music = music.audio_fadein(1.0).audio_fadeout(1.5)
        
        return music
    except Exception as e:
        print(f"⚠️ Audio error: {e}")
        return None


# =============================================================================
# MAIN VIDEO CREATION
# =============================================================================
def create_video(script_data, output_path):
    """Create a video from script data."""
    
    print(f"🎬 Creating V2 video: {output_path}")
    
    scenes = script_data.get('scenes', [])
    # Handle nested script format from script_formatter
    if 'script' in script_data and 'scenes' in script_data['script']:
        scenes = script_data['script']['scenes']
    else:
        scenes = script_data.get('scenes', [])
    
    # Create consistent starfield
    print("  ✨ Generating starfield...")
    starfield = create_starfield(WIDTH, HEIGHT, num_stars=250, seed=42)
    
    # Create clips
    clips = []
    for i, scene in enumerate(scenes):
        print(f"  🎬 Scene {i+1}/{len(scenes)}: {scene.get('text', '')[:35]}...")
        duration = scene.get('duration', DURATION_PER_SCENE)
        clip = create_scene_clip(scene, duration, starfield)
        clips.append(clip)
    
    # Concatenate
    print("  🔗 Joining scenes...")
    final_video = concatenate_videoclips(clips, method="compose")
    
    # Audio
    music_path = get_background_music()
    if music_path:
        print(f"  🎵 Adding: {os.path.basename(music_path)}")
        audio = create_audio_mix(music_path, final_video.duration)
        if audio:
            final_video = final_video.set_audio(audio)
    
    # Write
    print("  💾 Encoding...")
    final_video.write_videofile(
        output_path,
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        preset='medium',
        threads=4,
        logger=None
    )
    
    # Cleanup
    final_video.close()
    for clip in clips:
        clip.close()
    
    print(f"✅ Done: {output_path}")
    return True


# =============================================================================
# SCRIPT CONVERSION
# =============================================================================
def enhance_script(script_data):
    """Add V2 features to script data."""
    
    scenes = script_data.get('scenes', [])
    enhanced = []
    
    for i, scene in enumerate(scenes):
        s = scene.copy()
        text_lower = s.get('text', '').lower()
        
        # Detect planet
        for planet in ['earth', 'mars', 'jupiter', 'saturn', 'venus', 'sun', 'moon', 'black_hole']:
            pname = planet.replace('_', ' ')
            if pname in text_lower:
                s['planet'] = planet
                break
        else:
            planets = ['earth', 'mars', 'jupiter', 'saturn', 'sun']
            s['planet'] = planets[i % len(planets)]
        
        # Detect expression
        if any(w in text_lower for w in ['destroy', 'crash', 'die', 'burn', 'deadly', 'kill']):
            s['expression'] = 'scared'
            s['dramatic'] = True
        elif any(w in text_lower for w in ['amazing', 'incredible', 'wow', 'huge', 'massive', '!']):
            s['expression'] = 'shocked'
        elif '?' in s.get('text', ''):
            s['expression'] = 'looking_right'
        elif i == 0:
            s['expression'] = 'neutral'
        elif i == len(scenes) - 1:
            s['expression'] = 'shocked'
            s['dramatic'] = True
        else:
            s['expression'] = random.choice(['neutral', 'happy', 'looking_left'])
        
        # Positions
        s['text_position'] = 'top'
        positions = ['center', 'center', 'left', 'right']
        s['planet_position'] = positions[i % len(positions)]
        s['planet_size'] = random.randint(150, 200)
        
        enhanced.append(s)
    
    script_data['scenes'] = enhanced
    return script_data


def process_scripts():
    """Process pending scripts."""
    
    ensure_dirs()
    
    if not os.path.exists(SCRIPTS_DIR):
        print(f"📁 Creating: {SCRIPTS_DIR}")
        os.makedirs(SCRIPTS_DIR)
        return
    
    scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.json')]
    
    if not scripts:
        print("📭 No scripts to process")
        return
    
    print(f"📁 Found {len(scripts)} script(s)")
    
    for script_file in scripts:
        path = os.path.join(SCRIPTS_DIR, script_file)
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Enhance
            data = enhance_script(data)
            
            # Output path
            base = os.path.splitext(script_file)[0]
            out_path = os.path.join(OUTPUT_DIR, f"{base}.mp4")
            
            # Create video
            if create_video(data, out_path):
                data['rendered'] = True
                data['rendered_at'] = datetime.now().isoformat()
                with open(path, 'w') as f:
                    json.dump(data, f, indent=2)
        
        except Exception as e:
            print(f"❌ Error: {script_file}: {e}")
            import traceback
            traceback.print_exc()


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("🎬 ASTRO SHORTS V2 - Enhanced Video Renderer")
    print("   • Cartoon planets with eyes")
    print("   • Glow text effects")
    print("   • Word-by-word animation")
    print("   • Color-coded keywords")
    print("   • Shake effects")
    print("=" * 60)
    print()
    
    process_scripts()
    
    print()
    print("=" * 60)
    print("✅ Rendering complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
