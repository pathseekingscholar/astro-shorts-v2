"""
V5 Idea Generator - Smart Topic Selection
==========================================
Reads analytics/strategy to prioritize winning topics.
Generates ideas using Gemini with detailed director scripts.
"""

import os
import json
import random
import requests
from datetime import datetime

try:
    from style_selector import infer_topic_family_from_text, select_style, style_prompt_fragment
except ImportError:
    from scripts.style_selector import infer_topic_family_from_text, select_style, style_prompt_fragment

# =============================================================================
# CONFIG
# =============================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
IDEAS_FILE = "ideas.json"
STRATEGY_FILE = "data/strategy.json"

# =============================================================================
# DIRECTOR PROMPT
# =============================================================================
DIRECTOR_PROMPT = """You are a YouTube Shorts DIRECTOR creating viral astrophysics content.

{strategy_context}

Create a DETAILED video script about: {topic_hint}

Make it VISUALLY DYNAMIC:
- Use 2+ planets in some scenes (side by side comparisons)
- Match effects to emotions (shock = shake, huge = zoom)
- Vary positions (don't always center)
- Include BIG numbers that blow minds
- Make the planets feel CARTOONY, expressive, and full of personality
- Push richer color, motion, and dramatic composition like a premium animation
- Use cooler effects when appropriate: speed lines, lens pulse, energy burst, orbit sparkles, star swirl

Return ONLY valid JSON:

{{
  "idea": {{
    "topic": "specific topic name",
    "hook": "Hook question that grabs attention",
    "title": "YouTube title with numbers (under 50 chars)",
    "description": "Short description for YouTube",
    "tags": ["space", "astrophysics", "science"],
    "topic_family": "category like black_holes, scale, distances, stars"
  }},
  "metadata": {{
    "mood": "mind-blowing",
    "music_style": "epic",
    "background_search": "deep space galaxy nebula"
  }},
  "timeline": [
    {{
      "time_start": 0.0,
      "time_end": 4.0,
      "layers": [
        {{"type": "planet", "name": "earth", "position": "center", "size": "large",
         "expression": "thinking", "entry_animation": "pop_in", "effects": ["idle_bounce"]}}
      ],
      "text": {{"content": "Hook question?", "position": "top", "style": "word_by_word"}},
      "screen_effects": [],
      "dramatic_moment": false
    }},
    {{
      "time_start": 4.0,
      "time_end": 8.0,
      "layers": [
        {{"type": "planet", "name": "jupiter", "position": "right", "size": "large",
         "expression": "smug", "entry_animation": "slide_from_right", "effects": ["pulse"]}},
        {{"type": "planet", "name": "earth", "position": "left", "size": "small",
         "expression": "looking_right", "entry_animation": "none", "effects": []}}
      ],
      "text": {{"content": "Comparison with NUMBER", "position": "top", "style": "word_by_word"}},
      "screen_effects": [],
      "dramatic_moment": false
    }},
    {{
      "time_start": 8.0,
      "time_end": 12.0,
      "layers": [
        {{"type": "planet", "name": "sun", "position": "center", "size": "huge",
         "expression": "shocked", "entry_animation": "zoom_in", "effects": ["glow", "pulse"]}}
      ],
      "text": {{"content": "DRAMATIC reveal!", "position": "top", "style": "slam_in"}},
      "screen_effects": ["camera_shake", "flash"],
      "dramatic_moment": true
    }},
    {{
      "time_start": 12.0,
      "time_end": 16.0,
      "layers": [
        {{"type": "planet", "name": "black_hole", "position": "center", "size": "large",
         "expression": "neutral", "entry_animation": "fade_in", "effects": ["pulse"]}},
        {{"type": "planet", "name": "earth", "position": "bottom_right", "size": "tiny",
         "expression": "scared", "entry_animation": "pop_in", "effects": ["shake"]}}
      ],
      "text": {{"content": "Mind-blowing comparison", "position": "top", "style": "word_by_word"}},
      "screen_effects": ["vignette_pulse"],
      "dramatic_moment": false
    }},
    {{
      "time_start": 16.0,
      "time_end": 20.0,
      "layers": [
        {{"type": "planet", "name": "earth", "position": "center", "size": "medium",
         "expression": "excited", "entry_animation": "bounce_in", "effects": ["idle_bounce"]}}
      ],
      "text": {{"content": "Epic conclusion!", "position": "top", "style": "word_by_word"}},
      "screen_effects": [],
      "dramatic_moment": false
    }}
  ]
}}

OPTIONS:
- Planets: earth, mars, jupiter, saturn, sun, moon, neptune, venus, mercury, black_hole, neutron_star
- Expressions: neutral, happy, scared, shocked, excited, thinking, angry, smug, looking_left, looking_right, dead
- Positions: center, left, right, top, bottom, top_left, top_right, bottom_left, bottom_right
- Sizes: tiny, small, medium, large, huge
- Entry: pop_in, slide_from_left, slide_from_right, fade_in, zoom_in, bounce_in, spin_in, none
- Object Effects: idle_bounce, shake, pulse, glow, wobble, vibrate, float, orbit_sparkles
- Screen Effects: camera_shake, flash, vignette_pulse, chromatic_aberration, glitch, speed_lines, energy_burst, lens_pulse, star_swirl
- Text Styles: word_by_word, slam_in, typewriter
- Moods: epic, dramatic, mind-blowing, intense, chill, horror
- Music: epic, dramatic, cinematic, intense, chill

RULES:
1. 5 scenes, 4 seconds each = 20 seconds total
2. At least 2 scenes with MULTIPLE planets (comparisons)
3. Only 1-2 dramatic moments with heavy screen effects
4. Include SPECIFIC numbers (millions, billions, light-years)
5. Make it VIRAL - surprising, extreme, mind-blowing facts
"""

# =============================================================================
# TOPIC FAMILIES
# =============================================================================
TOPIC_FAMILIES = {
    "black_holes": [
        "How big is the largest black hole?",
        "What happens if you fall into a black hole?",
        "Black hole vs neutron star density",
        "Supermassive black hole at galaxy center",
        "How fast do black holes spin?",
    ],
    "scale": [
        "Size of Earth vs Jupiter vs Sun",
        "How many Earths fit in the Sun?",
        "Largest star ever discovered",
        "Size of the observable universe",
        "How small is Earth compared to the galaxy?",
    ],
    "distances": [
        "How long to reach the nearest star?",
        "Distance to the edge of the universe",
        "How far is Voyager 1 now?",
        "Speed of light travel times",
        "How wide is the Milky Way?",
    ],
    "time": [
        "Age of the universe",
        "How long until the Sun dies?",
        "Time dilation near black holes",
        "How old are the oldest stars?",
        "What will happen in 1 trillion years?",
    ],
    "extreme_physics": [
        "Neutron star teaspoon weight",
        "Temperature at the Sun's core",
        "Speed of a pulsar rotation",
        "Gravity on a neutron star",
        "Magnetar magnetic field strength",
    ],
    "planets": [
        "Raining diamonds on Neptune",
        "Why is Venus hotter than Mercury?",
        "Jupiter's Great Red Spot size",
        "Saturn's density vs water",
        "Mars vs Earth comparison",
    ],
}

# =============================================================================
# FUNCTIONS
# =============================================================================
def load_strategy():
    """Load strategy from analytics."""
    if os.path.exists(STRATEGY_FILE):
        try:
            with open(STRATEGY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def get_recent_topic_history(existing_ideas, window=16):
    """Return recent topic strings and families for diversity filtering."""
    recent = []
    for idea in existing_ideas[-window:]:
        status = idea.get("status")
        if status not in ["pending", "formatted", "rendered", "uploaded"]:
            continue

        idea_obj = idea.get("idea", idea)
        topic = str(idea_obj.get("topic", "")).strip()
        family = str(idea_obj.get("topic_family", "")).strip()
        if topic or family:
            recent.append({"topic": topic, "family": family})
    return recent


def choose_candidate(candidates, existing_ideas):
    """Pick a candidate that is not too close to recent history."""
    shuffled = list(candidates)
    random.shuffle(shuffled)
    for topic, reason in shuffled:
        if not is_duplicate(topic, existing_ideas):
            return topic, reason
    return shuffled[0] if shuffled else ("How big is the observable universe?", "Fallback topic")


def get_topic_hint(strategy, existing_ideas=None):
    """Select topic based on strategy while avoiding recent repetition."""
    existing_ideas = existing_ideas or []
    recent_history = get_recent_topic_history(existing_ideas)
    recent_families = [item["family"] for item in recent_history if item["family"]]
    blocked_topics = {item["topic"].lower() for item in recent_history if item["topic"]}

    top_families = strategy.get("top_performing_families", [])
    suggested = strategy.get("suggested_topics", [])
    candidates = []

    if top_families and random.random() < 0.5:
        eligible_families = [family for family in top_families[:3] if recent_families.count(family) < 2]
        family_pool = eligible_families or top_families[:3]
        family = random.choice(family_pool)
        if family in TOPIC_FAMILIES:
            for topic in TOPIC_FAMILIES[family]:
                if topic.lower() not in blocked_topics:
                    candidates.append((topic, f"Focus on {family} - your top performer!"))

    if suggested and random.random() < 0.6:
        for topic in suggested:
            if str(topic).lower() not in blocked_topics:
                candidates.append((topic, "Suggested by analytics"))

    all_families = list(TOPIC_FAMILIES.keys())
    low_cooldown = [family for family in all_families if recent_families.count(family) == 0]
    medium_cooldown = [family for family in all_families if recent_families.count(family) <= 1]
    family_pool = low_cooldown or medium_cooldown or all_families
    random.shuffle(family_pool)
    for family in family_pool:
        for topic in TOPIC_FAMILIES[family]:
            if topic.lower() not in blocked_topics:
                candidates.append((topic, f"Exploring {family}"))

    return choose_candidate(candidates, existing_ideas)


def load_existing_ideas():
    """Load existing ideas to avoid duplicates."""
    if os.path.exists(IDEAS_FILE):
        try:
            with open(IDEAS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return []


def is_duplicate(new_topic, existing_ideas):
    """Check if topic is too similar to existing."""
    new_words = set(new_topic.lower().split())
    
    for idea in existing_ideas[-20:]:  # Check last 20
        if idea.get("status") in ["pending", "formatted", "rendered"]:
            existing_topic = idea.get("idea", {}).get("topic", "")
            existing_words = set(existing_topic.lower().split())
            
            # If more than 60% overlap, it's a duplicate
            overlap = len(new_words & existing_words) / max(len(new_words), 1)
            if overlap > 0.6:
                return True
    
    return False


def build_strategy_context(strategy, style_plan):
    """Build a compact strategy context block for the model."""
    context_bits = []
    if strategy:
        top = strategy.get("top_performing_families", [])
        if top:
            context_bits.append(f"Best performing families: {', '.join(top[:3])}.")
        avoid = strategy.get("avoid_topics", []) or strategy.get("underperforming_topics", [])
        if avoid:
            avoid_topics = []
            for item in avoid[:3]:
                if isinstance(item, dict):
                    avoid_topics.append(str(item.get("topic", "")).strip())
                else:
                    avoid_topics.append(str(item).strip())
            avoid_topics = [topic for topic in avoid_topics if topic]
            if avoid_topics:
                context_bits.append(f"Avoid stale topics: {', '.join(avoid_topics)}.")

    if style_plan:
        context_bits.append(style_prompt_fragment(style_plan).strip())

    return "\n".join(context_bits).strip()


def generate_idea(topic_hint, strategy_context, style_plan=None):
    """Generate idea using Gemini."""
    
    if not GEMINI_API_KEY:
        print("❌ No GEMINI_API_KEY")
        return None
    
    prompt = DIRECTOR_PROMPT.format(
        topic_hint=topic_hint,
        strategy_context=strategy_context
    )
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    for attempt in range(3):
        try:
            print(f"🧠 Generating idea (attempt {attempt + 1})...")
            
            response = requests.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}]
            }, timeout=60)
            
            if response.status_code == 503:
                print("⚠️ Gemini overloaded, retrying...")
                import time
                time.sleep(5)
                continue
            
            if response.status_code == 200:
                data = response.json()
                text = data['candidates'][0]['content']['parts'][0]['text']
                
                # Extract JSON
                if '```json' in text:
                    text = text.split('```json')[1].split('```')[0]
                elif '```' in text:
                    text = text.split('```')[1].split('```')[0]
                
                script = json.loads(text.strip())
                print("✅ Idea generated!")
                return script
            else:
                print(f"❌ API error: {response.status_code}")
                print(response.text[:500])
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return None


def save_idea(idea_data, existing_ideas):
    """Save idea to ideas.json."""
    
    idea_entry = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        **idea_data
    }
    
    existing_ideas.append(idea_entry)
    
    # Keep only last 50 ideas
    if len(existing_ideas) > 50:
        existing_ideas = existing_ideas[-50:]
    
    with open(IDEAS_FILE, 'w') as f:
        json.dump(existing_ideas, f, indent=2)
    
    print(f"💾 Saved idea: {idea_data.get('idea', {}).get('title', 'Untitled')}")
    return idea_entry


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("🎬 V5 Idea Generator")
    print("=" * 60)
    
    # Load strategy
    strategy = load_strategy()
    if strategy:
        print(f"📊 Strategy loaded: {len(strategy.get('top_performing_families', []))} top families")
    else:
        print("📊 No strategy file, using default topics")
    
    # Load existing ideas first so the selector can avoid recent repetition
    existing_ideas = load_existing_ideas()

    # Get topic hint
    topic_hint, reason = get_topic_hint(strategy, existing_ideas)
    print(f"💡 Topic: {topic_hint}")
    print(f"   Reason: {reason}")

    topic_family = infer_topic_family_from_text(topic_hint)
    style_plan = select_style(
        strategy=strategy,
        topic_hint=topic_hint,
        topic_family=topic_family,
        existing_ideas=existing_ideas,
    )
    print(f"🎨 Style: {style_plan.get('style_id')} ({style_plan.get('label', style_plan.get('style_id'))})")
    
    # Build strategy context for prompt
    strategy_context = build_strategy_context(strategy, style_plan)
    
    # Generate idea
    idea_data = generate_idea(topic_hint, strategy_context, style_plan=style_plan)
    
    if not idea_data:
        print("❌ Failed to generate idea")
        return
    
    # Check for duplicates
    new_topic = idea_data.get("idea", {}).get("topic", "")
    if is_duplicate(new_topic, existing_ideas):
        print(f"⚠️ Topic too similar to recent ideas, regenerating...")
        # Try once more with different topic
        topic_hint, reason = get_topic_hint(strategy, existing_ideas)
        topic_family = infer_topic_family_from_text(topic_hint)
        style_plan = select_style(
            strategy=strategy,
            topic_hint=topic_hint,
            topic_family=topic_family,
            existing_ideas=existing_ideas,
        )
        strategy_context = build_strategy_context(strategy, style_plan)
        idea_data = generate_idea(topic_hint, strategy_context, style_plan=style_plan)
        
        if not idea_data:
            print("❌ Failed to generate unique idea")
            return

    idea_data["style_plan"] = style_plan
    idea_data["style_id"] = style_plan.get("style_id")
    idea_data.setdefault("metadata", {})
    idea_data["metadata"]["style_id"] = style_plan.get("style_id")
    idea_data["metadata"]["render_template"] = style_plan.get("render_template")
    idea_data["metadata"]["caption_font"] = style_plan.get("caption_font")
    idea_data["render_plan"] = {
        "style_id": style_plan.get("style_id"),
        "render_template": style_plan.get("render_template"),
        "background_mode": style_plan.get("background_mode"),
        "background_query": idea_data["metadata"].get("background_search", topic_hint),
        "background_video_path": "",
        "caption_font": style_plan.get("caption_font"),
        "music_style": style_plan.get("music_style"),
    }
    idea_data["metadata"]["render_plan"] = idea_data["render_plan"]

    # Save
    save_idea(idea_data, existing_ideas)
    
    # Print summary
    print()
    print("📋 Generated Idea:")
    print("-" * 50)
    print(f"   Title: {idea_data.get('idea', {}).get('title', 'N/A')}")
    print(f"   Topic: {idea_data.get('idea', {}).get('topic', 'N/A')}")
    print(f"   Mood: {idea_data.get('metadata', {}).get('mood', 'N/A')}")
    print(f"   Style: {idea_data.get('style_id', 'N/A')}")
    print(f"   Scenes: {len(idea_data.get('timeline', []))}")
    print("-" * 50)
    
    print()
    print("✅ Done!")


if __name__ == "__main__":
    main()
