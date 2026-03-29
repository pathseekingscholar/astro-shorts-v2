"""
V5 script formatter.

Takes pending ideas from ideas.json, validates them, preserves the selected style,
and writes renderer-ready JSON into scripts_output/.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

try:
    from style_selector import infer_topic_family_from_text, load_strategy, select_style
except ImportError:
    from scripts.style_selector import infer_topic_family_from_text, load_strategy, select_style

try:
    from music_generator import get_music_for_mood
except ImportError:
    try:
        from scripts.music_generator import get_music_for_mood
    except ImportError:
        get_music_for_mood = None


IDEAS_FILE = "ideas.json"
SCRIPTS_DIR = "scripts_output"
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def repo_relative_path(value):
    absolute = os.path.abspath(value)
    try:
        relative = os.path.relpath(absolute, ROOT_DIR)
    except ValueError:
        return value.replace("\\", "/")
    return relative.replace("\\", "/")


def load_ideas():
    if not os.path.exists(IDEAS_FILE):
        return []

    try:
        with open(IDEAS_FILE, "r", encoding="utf-8") as file_obj:
            return json.load(file_obj)
    except Exception:
        return []


def save_ideas(ideas):
    with open(IDEAS_FILE, "w", encoding="utf-8") as file_obj:
        json.dump(ideas, file_obj, indent=2)


def validate_script(script_data):
    timeline = script_data.get("timeline", [])
    if not timeline:
        return False, "No timeline"

    for index, scene in enumerate(timeline):
        if "time_start" not in scene or "time_end" not in scene:
            return False, f"Scene {index + 1} missing time_start/time_end"
        if "layers" not in scene or not scene["layers"]:
            return False, f"Scene {index + 1} missing layers"
        if "text" not in scene:
            return False, f"Scene {index + 1} missing text"

    return True, "Valid"


def get_pending_ideas(ideas):
    pending = [idea for idea in ideas if idea.get("status") == "pending"]
    return sorted(pending, key=lambda item: item.get("created_at", ""), reverse=True)


def select_or_reuse_style(idea_data):
    topic = idea_data.get("idea", {}).get("topic", "")
    existing_style = idea_data.get("style_plan") or {}
    if isinstance(existing_style, dict) and existing_style.get("style_id"):
        return existing_style

    return select_style(
        strategy=load_strategy(),
        topic_hint=topic,
        topic_family=infer_topic_family_from_text(topic),
        existing_ideas=[],
    )


def format_script(idea_data):
    valid, message = validate_script(idea_data)
    if not valid:
        print(f"Invalid script: {message}")
        return None

    style_plan = select_or_reuse_style(idea_data)
    metadata = dict(idea_data.get("metadata", {}))
    topic = idea_data.get("idea", {}).get("topic", "")

    metadata["style_id"] = style_plan.get("style_id")
    metadata["render_template"] = style_plan.get("render_template")
    metadata["caption_font"] = style_plan.get("caption_font")

    render_plan = {
        "style_id": style_plan.get("style_id"),
        "selected_style_id": style_plan.get("style_id"),
        "render_template": style_plan.get("render_template"),
        "background_mode": style_plan.get("background_mode"),
        "background_query": metadata.get("background_search", topic),
        "background_video_path": metadata.get("background_video_path", ""),
        "caption_font": style_plan.get("caption_font"),
        "music_style": style_plan.get("music_style"),
    }
    metadata["render_plan"] = render_plan

    return {
        "idea": idea_data.get("idea", {}),
        "metadata": metadata,
        "timeline": idea_data.get("timeline", []),
        "style_plan": style_plan,
        "style_id": style_plan.get("style_id"),
        "render_plan": render_plan,
        "formatted_at": datetime.now().isoformat(),
    }


def save_script(formatted_data, idea_id):
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    filename = f"script_{idea_id}.json"
    filepath = os.path.join(SCRIPTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as file_obj:
        json.dump(formatted_data, file_obj, indent=2)

    print(f"Saved script: {filename}")
    return filepath


def fetch_music_for_script(formatted_data):
    if not get_music_for_mood:
        return None

    metadata = formatted_data.get("metadata", {})
    style_plan = formatted_data.get("style_plan", {})
    mood = (
        (style_plan or {}).get("music_style")
        or metadata.get("music_style")
        or metadata.get("mood")
        or "cinematic"
    )
    timeline = formatted_data.get("timeline", [])
    duration = sum(max(0.0, scene.get("time_end", 0) - scene.get("time_start", 0)) for scene in timeline) + 2.5

    print(f"Fetching music for mood: {mood}")
    music_path = get_music_for_mood(mood, max(duration, 10.0))
    if music_path:
        normalized_path = repo_relative_path(music_path)
        formatted_data["music_path"] = normalized_path
        formatted_data.setdefault("render_plan", {})["music_path"] = normalized_path
        formatted_data.setdefault("metadata", {})["music_path"] = normalized_path
    return music_path


def main():
    print("=" * 60)
    print("V5 Script Formatter")
    print("=" * 60)

    ideas = load_ideas()
    if not ideas:
        print("No ideas found")
        return

    pending = get_pending_ideas(ideas)
    if not pending:
        print("No pending ideas")
        return

    print(f"Found {len(pending)} pending idea(s)")
    idea = pending[0]
    idea_id = idea.get("id", datetime.now().strftime("%Y%m%d_%H%M%S"))

    print(f"\nProcessing: {idea.get('idea', {}).get('title', 'Untitled')}")
    formatted = format_script(idea)
    if not formatted:
        for index, item in enumerate(ideas):
            if item.get("id") == idea_id:
                ideas[index]["status"] = "failed"
                ideas[index]["error"] = "Invalid script structure"
                break
        save_ideas(ideas)
        return

    fetch_music_for_script(formatted)
    save_script(formatted, idea_id)

    for index, item in enumerate(ideas):
        if item.get("id") == idea_id:
            ideas[index]["status"] = "formatted"
            ideas[index]["formatted_at"] = datetime.now().isoformat()
            ideas[index]["style_plan"] = formatted.get("style_plan", {})
            ideas[index]["style_id"] = formatted.get("style_id")
            break

    save_ideas(ideas)
    print("\nDone.")


if __name__ == "__main__":
    main()
