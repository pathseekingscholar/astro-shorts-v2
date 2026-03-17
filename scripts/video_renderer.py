"""
V5 Video Renderer - Advanced Features
======================================
- Multiple objects per frame with layering
- Entry/exit animations
- Per-object effects (shake, glow, spin, pulse)
- Screen effects (flash, chromatic aberration, camera shake)
- Text styles (word_by_word, slam_in, typewriter)
- Music integration
- Optional background images
"""

import os
import json
import random
import math
import textwrap
from datetime import datetime

from moviepy.editor import VideoClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
import numpy as np

# Import asset fetcher
try:
    from asset_fetcher import fetch_assets_for_script
except ImportError:
    fetch_assets_for_script = None

# =============================================================================
# CONFIG
# =============================================================================
WIDTH = 1080
HEIGHT = 1920
FPS = 30

SCRIPTS_DIR = "scripts_output"
OUTPUT_DIR = "videos_output"
AUDIO_DIR = "assets/audio"

COLORS = {
    'background': (8, 8, 24),
    'text_white': (255, 255, 255),
    'text_yellow': (255, 220, 0),
    'text_cyan': (0, 255, 255),
    'text_red': (255, 80, 80),
    'text_pink': (255, 100, 200),
    'glow_blue': (0, 180, 255),
    'glow_pink': (255, 100, 200),
}

POSITIONS = {
    'center': (0.5, 0.5),
    'left': (0.28, 0.5),
    'right': (0.72, 0.5),
    'top': (0.5, 0.3),
    'bottom': (0.5, 0.7),
    'top_left': (0.28, 0.3),
    'top_right': (0.72, 0.3),
    'bottom_left': (0.28, 0.7),
    'bottom_right': (0.72, 0.7),
}

SIZES = {
    'tiny': 50,
    'small': 90,
    'medium': 150,
    'large': 210,
    'huge': 280,
}

# =============================================================================
# FONT
# =============================================================================
def get_font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                continue
    return ImageFont.load_default()

# =============================================================================
# EASING FUNCTIONS
# =============================================================================
def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)

def ease_out_elastic(t):
    if t == 0 or t == 1:
        return t
    return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1

def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)

# =============================================================================
# STARFIELD / BACKGROUND
# =============================================================================
def create_starfield(bg_image_path=None):
    """Create background - either from image or procedural starfield."""
    
    # Try to use background image
    if bg_image_path and os.path.exists(bg_image_path):
        try:
            img = Image.open(bg_image_path).convert('RGB')
            img = img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            # Darken for text visibility
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.4)
            print(f"🖼️ Using background image")
            return img
        except Exception as e:
            print(f"⚠️ Could not load background: {e}")
    
    # Procedural starfield
    random.seed(42)
    img = Image.new('RGB', (WIDTH, HEIGHT), COLORS['background'])
    draw = ImageDraw.Draw(img)
    
    # Distant stars
    for _ in range(300):
        x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
        b = random.randint(40, 100)
        draw.point((x, y), fill=(b, b, b + 20))
    
    # Medium stars
    for _ in range(100):
        x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
        b = random.randint(120, 200)
        draw.ellipse([x, y, x+2, y+2], fill=(b, b, b))
    
    # Bright stars
    for _ in range(25):
        x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
        for r in range(5, 0, -1):
            a = 60 - r * 10
            draw.ellipse([x-r, y-r, x+r, y+r], fill=(80+a, 80+a, 120+a))
        draw.ellipse([x-1, y-1, x+1, y+1], fill=(255, 255, 255))
    
    # Nebula tint
    nebula = Image.new('RGB', (WIDTH, HEIGHT), (20, 10, 40))
    return Image.blend(img, nebula, 0.12)

# =============================================================================
# ANIMATIONS
# =============================================================================
def apply_entry_animation(progress, anim_type, duration=0.3):
    if anim_type == 'none' or progress > duration:
        return {'scale': 1.0, 'offset': (0, 0), 'alpha': 1.0}
    
    t = progress / duration
    
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
    elif anim_type == 'spin_in':
        return {'scale': ease_out_cubic(t), 'offset': (0, 0), 'alpha': 1.0}
    
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
            alpha = int(255 * (r / max_r))
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=alpha)
        
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
            slice_img = img.crop((0, y, img.width, y + h))
            result.paste(slice_img, (random.randint(-25, 25), y))
        return result
    
    return img

# =============================================================================
# PLANET DRAWING
# =============================================================================
def draw_planet(draw, cx, cy, radius, planet_type='earth', expression='neutral'):
    planets = {
        'earth': {'ocean': (40, 100, 180), 'land': (60, 140, 80)},
        'mars': {'base': (180, 80, 60)},
        'jupiter': {'base': (200, 160, 120), 'bands': [(180, 140, 100), (220, 180, 140)]},
        'saturn': {'base': (210, 190, 150), 'ring': (180, 160, 130)},
        'sun': {'base': (255, 200, 50)},
        'moon': {'base': (180, 180, 180), 'crater': (140, 140, 140)},
        'neptune': {'base': (60, 100, 200)},
        'venus': {'base': (230, 180, 100)},
        'mercury': {'base': (160, 150, 140)},
        'black_hole': {'base': (10, 10, 10)},
        'neutron_star': {'base': (200, 200, 255)},
    }
    
    config = planets.get(planet_type, planets['earth'])
    
    if planet_type == 'sun':
        for i in range(8, 0, -1):
            r = radius + i * (radius * 0.08)
            intensity = 255 - i * 20
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(intensity, int(intensity*0.6), 0))
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=config['base'])
    
    elif planet_type == 'earth':
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=config['ocean'])
        land = config['land']
        draw.ellipse([cx-radius*0.7, cy-radius*0.5, cx-radius*0.2, cy+radius*0.1], fill=land)
        draw.ellipse([cx-radius*0.6, cy+radius*0.1, cx-radius*0.3, cy+radius*0.5], fill=land)
        draw.ellipse([cx+radius*0.1, cy-radius*0.4, cx+radius*0.5, cy+radius*0.1], fill=land)
        draw.ellipse([cx+radius*0.15, cy, cx+radius*0.45, cy+radius*0.5], fill=land)
        draw.ellipse([cx+radius*0.3, cy-radius*0.6, cx+radius*0.7, cy-radius*0.1], fill=land)
    
    elif planet_type == 'jupiter':
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=config['base'])
        bands = config['bands']
        for i in range(7):
            band_y = cy - radius + (i * 2 * radius // 7)
            for dy in range(radius // 5):
                y = band_y + dy
                dist = abs(y - cy)
                if dist < radius:
                    x_ext = int(math.sqrt(radius**2 - dist**2))
                    draw.line([(cx - x_ext, y), (cx + x_ext, y)], fill=bands[i % 2], width=1)
        draw.ellipse([cx+radius*0.15, cy+radius*0.1, cx+radius*0.45, cy+radius*0.26], fill=(180, 100, 80))
    
    elif planet_type == 'saturn':
        ring = config['ring']
        for i in range(3):
            ring_r = radius * (1.3 + i * 0.15)
            draw.arc([cx-ring_r, cy-radius*0.2, cx+ring_r, cy+radius*0.2], 0, 180, fill=ring, width=8-i*2)
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=config['base'])
        for i in range(3):
            ring_r = radius * (1.3 + i * 0.15)
            draw.arc([cx-ring_r, cy-radius*0.2, cx+ring_r, cy+radius*0.2], 180, 360, fill=ring, width=8-i*2)
    
    elif planet_type == 'black_hole':
        for i in range(5, 0, -1):
            r = radius * (1.2 + i * 0.1)
            draw.ellipse([cx-r, cy-int(r*0.3), cx+r, cy+int(r*0.3)], fill=(80+i*15, 30+i*10, 120+i*10))
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=(5, 5, 5))
    
    elif planet_type == 'neutron_star':
        for i in range(6, 0, -1):
            r = radius + i * (radius * 0.1)
            draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(150+i*15, 150+i*15, 255))
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=config['base'])
    
    elif planet_type == 'moon':
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=config['base'])
        craters = [(0.3, -0.2, 0.15), (-0.2, 0.3, 0.12), (0.4, 0.2, 0.1), (-0.3, -0.3, 0.08)]
        for dx, dy, size in craters:
            cr = size * radius
            draw.ellipse([cx+dx*radius-cr, cy+dy*radius-cr, cx+dx*radius+cr, cy+dy*radius+cr], 
                        fill=config.get('crater', (140, 140, 140)))
    
    else:
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=config.get('base', (150, 150, 150)))
    
    # Draw eyes
    draw_eyes(draw, cx, cy, radius, expression, planet_type)

def draw_eyes(draw, cx, cy, radius, expression='neutral', planet_type='earth'):
    expressions = {
        'neutral': {'scale': 1.0, 'pupil_offset': (0, 0)},
        'happy': {'scale': 1.0, 'happy': True},
        'scared': {'scale': 1.5, 'small_pupil': True},
        'shocked': {'scale': 1.7, 'small_pupil': True},
        'excited': {'scale': 1.3},
        'thinking': {'scale': 1.0, 'pupil_offset': (0.2, -0.2)},
        'angry': {'scale': 0.9, 'angry': True},
        'smug': {'scale': 0.85, 'pupil_offset': (0.15, 0.1)},
        'looking_left': {'scale': 1.0, 'pupil_offset': (-0.35, 0)},
        'looking_right': {'scale': 1.0, 'pupil_offset': (0.35, 0)},
        'sleeping': {'scale': 1.0, 'closed': True},
        'dead': {'scale': 1.2, 'x_eyes': True},
    }
    
    expr = expressions.get(expression, expressions['neutral'])
    
    eye_scale = expr.get('scale', 1.0)
    spacing = radius * 0.32
    eye_y = cy - radius * 0.08
    eye_r = int(radius * 0.18 * eye_scale)
    pupil_r = int(eye_r * (0.35 if expr.get('small_pupil') else 0.5))
    
    eye_white = (255, 255, 220) if planet_type == 'sun' else (255, 255, 255)
    
    for i, ex in enumerate([cx - spacing, cx + spacing]):
        if expr.get('happy'):
            draw.arc([ex-eye_r, eye_y-eye_r, ex+eye_r, eye_y+eye_r], 200, 340, fill=(0,0,0), width=max(4, eye_r//3))
        elif expr.get('closed'):
            draw.line([(ex - eye_r, eye_y), (ex + eye_r, eye_y)], fill=(0, 0, 0), width=4)
        elif expr.get('x_eyes'):
            draw.line([(ex-eye_r, eye_y-eye_r), (ex+eye_r, eye_y+eye_r)], fill=(0,0,0), width=4)
            draw.line([(ex-eye_r, eye_y+eye_r), (ex+eye_r, eye_y-eye_r)], fill=(0,0,0), width=4)
        elif expr.get('angry'):
            draw.ellipse([ex-eye_r, eye_y-eye_r, ex+eye_r, eye_y+eye_r], fill=eye_white, outline=(0,0,0), width=2)
            if i == 0:
                draw.line([(ex-eye_r-5, eye_y-eye_r+5), (ex+eye_r+5, eye_y-eye_r-8)], fill=(0,0,0), width=5)
            else:
                draw.line([(ex-eye_r-5, eye_y-eye_r-8), (ex+eye_r+5, eye_y-eye_r+5)], fill=(0,0,0), width=5)
            offset = expr.get('pupil_offset', (0, 0.1))
            px = ex + int(offset[0] * eye_r)
            py = eye_y + int(offset[1] * eye_r)
            draw.ellipse([px-pupil_r, py-pupil_r, px+pupil_r, py+pupil_r], fill=(0, 0, 0))
        else:
            draw.ellipse([ex-eye_r, eye_y-eye_r, ex+eye_r, eye_y+eye_r], fill=eye_white, outline=(0,0,0), width=2)
            offset = expr.get('pupil_offset', (0, 0))
            px = ex + int(offset[0] * eye_r)
            py = eye_y + int(offset[1] * eye_r)
            draw.ellipse([px-pupil_r, py-pupil_r, px+pupil_r, py+pupil_r], fill=(0, 0, 0))
            hl_r = max(3, pupil_r // 2)
            draw.ellipse([px-pupil_r*0.4-hl_r, py-pupil_r*0.4-hl_r,
                         px-pupil_r*0.4+hl_r, py-pupil_r*0.4+hl_r], fill=(255, 255, 255))

# =============================================================================
# TEXT RENDERING
# =============================================================================
def render_text(img, text_config, progress, frame_num):
    content = text_config.get('content', '')
    if not content:
        return img
    
    position = text_config.get('position', 'top')
    style = text_config.get('style', 'word_by_word')
    
    font = get_font(46)
    draw = ImageDraw.Draw(img)
    
    y = 180 if position == 'top' else HEIGHT - 300
    
    # Apply text style
    if style == 'word_by_word':
        words = content.split()
        num_show = max(1, int(len(words) * min(progress * 1.3, 1.0)))
        content = ' '.join(words[:num_show])
    elif style == 'slam_in':
        if progress < 0.15:
            font = get_font(int(46 * (3.0 - 2.0 * (progress / 0.15))))
    elif style == 'typewriter':
        num_chars = int(len(content) * progress)
        content = content[:num_chars]
    
    result = img.convert('RGBA')
    
    # Word wrap
    bbox = draw.textbbox((0, 0), content, font=font)
    if bbox[2] - bbox[0] > 900:
        content = textwrap.fill(content, width=24)
    
    lines = content.split('\n')
    line_height = 56
    
    for li, line in enumerate(lines):
        ly = y + li * line_height
        bbox = draw.textbbox((0, 0), line, font=font)
        lx = (WIDTH - (bbox[2] - bbox[0])) // 2
        
        for word in line.split():
            word_lower = word.lower().strip('.,!?')
            
            # Color coding
            if any(c.isdigit() for c in word):
                color = COLORS['text_yellow']
                glow = (255, 200, 0)
            elif word_lower in ['earth', 'mars', 'jupiter', 'saturn', 'sun', 'moon', 'neptune']:
                color = COLORS['text_cyan']
                glow = COLORS['glow_blue']
            else:
                color = COLORS['text_white']
                glow = COLORS['glow_blue']
            
            # Glow
            glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_layer)
            for off in range(5, 0, -1):
                alpha = int(50 * (1 - off/5))
                for dx in range(-off, off+1, 2):
                    for dy in range(-off, off+1, 2):
                        gd.text((lx+dx, ly+dy), word, font=font, fill=(*glow, alpha))
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(2))
            result = Image.alpha_composite(result, glow_layer)
            
            # Outline
            ol = Image.new('RGBA', img.size, (0, 0, 0, 0))
            od = ImageDraw.Draw(ol)
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    od.text((lx+dx, ly+dy), word, font=font, fill=(0, 0, 0, 255))
            result = Image.alpha_composite(result, ol)
            
            # Text
            tl = Image.new('RGBA', img.size, (0, 0, 0, 0))
            td = ImageDraw.Draw(tl)
            td.text((lx, ly), word, font=font, fill=(*color, 255))
            result = Image.alpha_composite(result, tl)
            
            wb = draw.textbbox((0, 0), word + ' ', font=font)
            lx += wb[2] - wb[0]
    
    return result.convert('RGB')

# =============================================================================
# FRAME RENDERING
# =============================================================================
def render_frame(scene, frame_num, total_frames, starfield):
    progress = frame_num / max(total_frames - 1, 1)
    
    frame = starfield.copy()
    draw = ImageDraw.Draw(frame)
    
    layers = scene.get('layers', [])
    text_config = scene.get('text', {})
    screen_effects = scene.get('screen_effects', [])
    
    # Draw layers
    for layer in layers:
        layer_type = layer.get('type', 'planet')
        name = layer.get('name', 'earth')
        position = layer.get('position', 'center')
        size = layer.get('size', 'medium')
        expression = layer.get('expression', 'neutral')
        entry_anim = layer.get('entry_animation', 'pop_in')
        effects = layer.get('effects', [])
        
        pos_norm = POSITIONS.get(position, (0.5, 0.5))
        cx = int(pos_norm[0] * WIDTH)
        cy = int(pos_norm[1] * HEIGHT)
        radius = SIZES.get(size, 150)
        
        # Entry animation
        entry = apply_entry_animation(progress, entry_anim)
        radius = int(radius * entry.get('scale', 1.0))
        cx += int(entry.get('offset', (0, 0))[0])
        cy += int(entry.get('offset', (0, 0))[1])
        
        # Object effects
        for effect in effects:
            eff = apply_object_effect(frame_num, effect)
            if 'offset' in eff:
                cx += int(eff['offset'][0])
                cy += int(eff['offset'][1])
            if 'scale_mod' in eff:
                radius = int(radius * eff['scale_mod'])
        
        if radius > 10 and layer_type == 'planet':
            draw_planet(draw, cx, cy, radius, name, expression)
    
    # Text
    if text_config:
        frame = render_text(frame, text_config, progress, frame_num)
    
    # Screen effects
    for effect in screen_effects:
        frame = apply_screen_effect(frame, effect, frame_num)
    
    return np.array(frame)

# =============================================================================
# VIDEO CREATION
# =============================================================================
def create_video(script_data, output_path, music_path=None, bg_image=None):
    print(f"🎬 Creating video: {output_path}")
    
    timeline = script_data.get('timeline', [])
    if not timeline:
        print("❌ No timeline in script")
        return False
    
    starfield = create_starfield(bg_image)
    
    clips = []
    for i, scene in enumerate(timeline):
        start = scene.get('time_start', 0)
        end = scene.get('time_end', 4)
        duration = end - start
        
        text_preview = scene.get('text', {}).get('content', '')[:35]
        print(f"  🎬 Scene {i+1}/{len(timeline)}: {text_preview}...")
        
        total_frames = int(duration * FPS)
        
        def make_frame(t, scene=scene, total_frames=total_frames):
            frame_num = min(int(t * FPS), total_frames - 1)
            return render_frame(scene, frame_num, total_frames, starfield)
        
        clips.append(VideoClip(make_frame, duration=duration))
    
    print("  🔗 Joining clips...")
    video = concatenate_videoclips(clips, method="compose")
    
    # Add audio
    if music_path and os.path.exists(music_path):
        try:
            audio = AudioFileClip(music_path)
            if audio.duration < video.duration:
                from moviepy.editor import concatenate_audioclips
                loops = int(video.duration / audio.duration) + 1
                audio = concatenate_audioclips([audio] * loops)
            audio = audio.subclip(0, video.duration).volumex(0.3)
            audio = audio.audio_fadein(0.5).audio_fadeout(1.0)
            video = video.set_audio(audio)
            print(f"  🎵 Added music")
        except Exception as e:
            print(f"  ⚠️ Music error: {e}")
    else:
        # Try to find any music in assets/audio
        if os.path.exists(AUDIO_DIR):
            audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith(('.mp3', '.wav'))]
            if audio_files:
                try:
                    audio_path = os.path.join(AUDIO_DIR, random.choice(audio_files))
                    audio = AudioFileClip(audio_path)
                    if audio.duration < video.duration:
                        from moviepy.editor import concatenate_audioclips
                        loops = int(video.duration / audio.duration) + 1
                        audio = concatenate_audioclips([audio] * loops)
                    audio = audio.subclip(0, video.duration).volumex(0.3)
                    audio = audio.audio_fadein(0.5).audio_fadeout(1.0)
                    video = video.set_audio(audio)
                    print(f"  🎵 Added music: {audio_files[0]}")
                except:
                    pass
    
    print("  💾 Encoding...")
    video.write_videofile(output_path, fps=FPS, codec='libx264',
                         preset='medium', threads=4, logger=None)
    
    video.close()
    for c in clips:
        c.close()
    
    print(f"✅ Done: {output_path}")
    return True

# =============================================================================
# MAIN
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
    
    print(f"📁 Found {len(scripts)} script(s)")
    
    for script_file in scripts:
        script_path = os.path.join(SCRIPTS_DIR, script_file)
        
        try:
            with open(script_path, 'r') as f:
                script_data = json.load(f)
            
            # Check if already rendered
            if script_data.get('rendered'):
                print(f"⏭️ Already rendered: {script_file}")
                continue
            
            # Fetch assets
            assets = {"music": None, "background": None}
            if fetch_assets_for_script:
                try:
                    pixabay_key = os.environ.get('PIXABAY_API_KEY', '')
                    assets = fetch_assets_for_script(script_data, pixabay_key)
                except:
                    pass
            
            # Create video
            output_path = os.path.join(OUTPUT_DIR, script_file.replace('.json', '.mp4'))
            
            if create_video(script_data, output_path, assets.get('music'), assets.get('background')):
                script_data['rendered'] = True
                script_data['rendered_at'] = datetime.now().isoformat()
                script_data['video_path'] = output_path
                
                with open(script_path, 'w') as f:
                    json.dump(script_data, f, indent=2)
                    
        except Exception as e:
            print(f"❌ Error processing {script_file}: {e}")
            import traceback
            traceback.print_exc()


def main():
    print("=" * 60)
    print("🎬 V5 Video Renderer")
    print("=" * 60)
    process_scripts()
    print("=" * 60)
    print("✅ Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
