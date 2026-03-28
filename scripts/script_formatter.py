"""
V5 Script Formatter
====================
Takes ideas from ideas.json and prepares them for video rendering.
In V5, ideas already contain the full timeline, so this mainly:
- Validates the script structure
- Moves to scripts_output/
- Fetches assets (music, images)
"""

import os
import json
from datetime import datetime

# Import music fetcher
try:
    from music_generator import get_music_for_mood
except ImportError:
    try:
        from scripts.music_generator import get_music_for_mood
    except ImportError:
        get_music_for_mood = None

# =============================================================================
# CONFIG
# =============================================================================
IDEAS_FILE = "ideas.json"
SCRIPTS_DIR = "scripts_output"

# =============================================================================
# FUNCTIONS
# =============================================================================
def load_ideas():
    """Load ideas from ideas.json."""
    if not os.path.exists(IDEAS_FILE):
        return []
    
    try:
        with open(IDEAS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []


def save_ideas(ideas):
    """Save ideas back to ideas.json."""
    with open(IDEAS_FILE, 'w') as f:
        json.dump(ideas, f, indent=2)


def validate_script(script_data):
    """Validate that script has required fields."""
    
    # Check for timeline
    timeline = script_data.get('timeline', [])
    if not timeline:
        return False, "No timeline"
    
    # Check each scene
    for i, scene in enumerate(timeline):
        if 'time_start' not in scene or 'time_end' not in scene:
            return False, f"Scene {i+1} missing time_start/time_end"
        
        if 'layers' not in scene or not scene['layers']:
            return False, f"Scene {i+1} missing layers"
        
        if 'text' not in scene:
            return False, f"Scene {i+1} missing text"
    
    return True, "Valid"


def get_pending_ideas(ideas):
    """Get ideas with status 'pending'."""
    pending = [i for i in ideas if i.get('status') == 'pending']
    return sorted(
        pending,
        key=lambda item: item.get('created_at', ''),
        reverse=True,
    )


def format_script(idea_data):
    """
    Format/validate an idea for rendering.
    V5 ideas already contain full timeline, so mainly validation.
    """
    
    # Validate
    valid, msg = validate_script(idea_data)
    if not valid:
        print(f"❌ Invalid script: {msg}")
        return None
    
    # The idea_data already has the full script structure
    # Just ensure it has all needed fields
    
    formatted = {
        "idea": idea_data.get("idea", {}),
        "metadata": idea_data.get("metadata", {}),
        "timeline": idea_data.get("timeline", []),
        "formatted_at": datetime.now().isoformat(),
    }
    
    return formatted


def save_script(formatted_data, idea_id):
    """Save formatted script to scripts_output/."""
    
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    
    # Clear old scripts (keep only latest)
    existing = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.json')]
    for old_file in existing:
        old_path = os.path.join(SCRIPTS_DIR, old_file)
        # Check if already rendered
        try:
            with open(old_path, 'r') as f:
                old_data = json.load(f)
            if old_data.get('rendered'):
                os.remove(old_path)
                print(f"🗑️ Removed old rendered script: {old_file}")
        except:
            pass
    
    # Save new script
    filename = f"script_{idea_id}.json"
    filepath = os.path.join(SCRIPTS_DIR, filename)
    
    with open(filepath, 'w') as f:
        json.dump(formatted_data, f, indent=2)
    
    print(f"💾 Saved script: {filename}")
    return filepath


def fetch_music_for_script(formatted_data):
    """Pre-fetch music for the script."""
    
    if not get_music_for_mood:
        return
    
    metadata = formatted_data.get('metadata', {})
    mood = metadata.get('music_style') or metadata.get('mood') or 'cinematic'
    timeline = formatted_data.get('timeline', [])
    duration = sum(
        max(0.0, scene.get('time_end', 0) - scene.get('time_start', 0))
        for scene in timeline
    ) + 2.5
    
    print(f"🎵 Fetching music for mood: {mood}")
    get_music_for_mood(mood, max(duration, 10.0))


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 60)
    print("📝 V5 Script Formatter")
    print("=" * 60)
    
    # Load ideas
    ideas = load_ideas()
    
    if not ideas:
        print("📭 No ideas found")
        return
    
    # Get pending ideas
    pending = get_pending_ideas(ideas)
    
    if not pending:
        print("📭 No pending ideas")
        return
    
    print(f"📋 Found {len(pending)} pending idea(s)")
    
    # Process first pending idea
    idea = pending[0]
    idea_id = idea.get('id', datetime.now().strftime("%Y%m%d_%H%M%S"))
    
    print(f"\n📝 Processing: {idea.get('idea', {}).get('title', 'Untitled')}")
    
    # Format script
    formatted = format_script(idea)
    
    if not formatted:
        # Mark as failed
        for i, item in enumerate(ideas):
            if item.get('id') == idea_id:
                ideas[i]['status'] = 'failed'
                ideas[i]['error'] = 'Invalid script structure'
                break
        save_ideas(ideas)
        return
    
    # Save script
    save_script(formatted, idea_id)
    
    # Pre-fetch music
    fetch_music_for_script(formatted)
    
    # Update idea status
    for i, item in enumerate(ideas):
        if item.get('id') == idea_id:
            ideas[i]['status'] = 'formatted'
            ideas[i]['formatted_at'] = datetime.now().isoformat()
            break
    
    save_ideas(ideas)
    
    print()
    print("✅ Done!")


if __name__ == "__main__":
    main()
