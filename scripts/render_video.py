"""
Render orchestrator for Astro Shorts.

Routes scripts through the active renderer, fetches reusable assets, and keeps
script metadata in sync with the produced output.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from background_video_fetcher import get_background_video
except ImportError:
    from scripts.background_video_fetcher import get_background_video

try:
    from music_generator import get_music_for_mood
except ImportError:
    from scripts.music_generator import get_music_for_mood

try:
    from space_image_fetcher import get_space_background_for_script
except ImportError:
    from scripts.space_image_fetcher import get_space_background_for_script


ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts_output"
VIDEOS_DIR = ROOT_DIR / "videos_output"
REMOTION_STYLE_IDS = {"planet_character", "educational_voiceless", "character_explainer"}


def latest_script_path() -> Path | None:
    scripts = sorted(SCRIPTS_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return scripts[0] if scripts else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route a script through the active renderer.")
    parser.add_argument("script", nargs="?", help="Optional script JSON path")
    parser.add_argument("--preview", action="store_true", help="Generate a faster preview output")
    parser.add_argument("--style", help="Optional explicit style override")
    return parser.parse_args()


def load_script(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_script(path: Path, script_data: dict) -> None:
    path.write_text(json.dumps(script_data, indent=2), encoding="utf-8")


def repo_relative_path(value: str | Path) -> str:
    path = Path(value)
    try:
        if path.is_absolute():
            return str(path.relative_to(ROOT_DIR)).replace("\\", "/")
    except ValueError:
        pass
    return str(path).replace("\\", "/")


def normalize_style_id(value: str | None) -> str | None:
    candidate = str(value or "").strip()
    return candidate if candidate in REMOTION_STYLE_IDS else None


def selected_style_id(script_data: dict, override: str | None = None) -> str:
    render_plan = script_data.get("render_plan") or script_data.get("renderPlan") or {}
    style_plan = script_data.get("style_plan") or {}
    metadata = script_data.get("metadata") or {}

    for candidate in (
        override,
        style_plan.get("style_id") if isinstance(style_plan, dict) else None,
        render_plan.get("selected_style_id"),
        render_plan.get("style_id"),
        render_plan.get("render_template"),
        metadata.get("style_id"),
        metadata.get("render_template"),
        metadata.get("render_style"),
        script_data.get("style_id"),
    ):
        resolved = normalize_style_id(candidate)
        if resolved:
            return resolved

    return "planet_character"


def use_remotion(style_id: str) -> bool:
    return style_id in REMOTION_STYLE_IDS


def script_duration_seconds(script_data: dict) -> float:
    timeline = script_data.get("timeline", [])
    total = 0.0
    for scene in timeline:
        start = float(scene.get("time_start", 0.0))
        end = float(scene.get("time_end", start))
        total += max(0.5, end - start)
    hook = 2.2 if total else 0.0
    return max(10.0, total + hook)


def ensure_render_plan(script_data: dict, style_id: str) -> dict:
    render_plan = dict(script_data.get("render_plan") or script_data.get("renderPlan") or {})
    metadata = dict(script_data.get("metadata") or {})
    style_plan = script_data.get("style_plan") or {}
    topic = (
        script_data.get("idea", {}).get("topic")
        or script_data.get("idea", {}).get("title")
        or metadata.get("background_search")
        or "space facts"
    )

    render_plan["style_id"] = style_id
    render_plan["selected_style_id"] = style_id
    render_plan["render_template"] = render_plan.get("render_template") or metadata.get("render_template") or style_id
    render_plan["background_query"] = (
        render_plan.get("background_query")
        or metadata.get("background_search")
        or topic
    )
    render_plan["caption_font"] = (
        render_plan.get("caption_font")
        or metadata.get("caption_font")
        or (style_plan.get("caption_font") if isinstance(style_plan, dict) else None)
        or "Montserrat ExtraBold"
    )
    render_plan["music_style"] = (
        render_plan.get("music_style")
        or metadata.get("music_style")
        or metadata.get("mood")
        or (style_plan.get("music_style") if isinstance(style_plan, dict) else None)
        or "cinematic"
    )
    render_plan["background_mode"] = (
        render_plan.get("background_mode")
        or metadata.get("background_mode")
        or (style_plan.get("background_mode") if isinstance(style_plan, dict) else None)
        or ("gameplay" if style_id == "character_explainer" else "nasa_space")
    )

    metadata["style_id"] = style_id
    metadata["render_template"] = render_plan["render_template"]
    metadata["caption_font"] = render_plan["caption_font"]
    metadata["music_style"] = render_plan["music_style"]
    metadata["background_search"] = render_plan["background_query"]

    script_data["style_id"] = style_id
    script_data["render_plan"] = render_plan
    script_data["metadata"] = metadata
    return render_plan


def attach_music(script_data: dict, render_plan: dict) -> None:
    duration_seconds = script_duration_seconds(script_data)
    mood = render_plan.get("music_style") or "cinematic"
    music_path = get_music_for_mood(str(mood), duration_seconds)
    if not music_path:
        return

    normalized_path = repo_relative_path(music_path)
    render_plan["music_path"] = normalized_path
    script_data["music_path"] = normalized_path
    script_data.setdefault("metadata", {})["music_path"] = normalized_path


def attach_space_background(script_data: dict, render_plan: dict) -> None:
    image_path = get_space_background_for_script(script_data)
    if not image_path:
        return

    normalized_path = repo_relative_path(image_path)
    render_plan["background_image_path"] = normalized_path
    script_data["background_path"] = normalized_path
    script_data.setdefault("metadata", {})["background_image_path"] = normalized_path


def attach_background_video(script_data: dict, render_plan: dict, style_id: str) -> None:
    if style_id != "character_explainer":
        return

    topic = (
        script_data.get("idea", {}).get("topic")
        or script_data.get("idea", {}).get("title")
        or render_plan.get("background_query")
        or "minecraft parkour"
    )
    preferred_query = (
        render_plan.get("background_video_query")
        or ("minecraft parkour" if render_plan.get("background_mode") == "gameplay" else render_plan.get("background_query"))
    )
    background_video_path = get_background_video(
        style_id,
        topic=str(topic),
        query=preferred_query,
    )
    if not background_video_path:
        return

    normalized_path = repo_relative_path(background_video_path)
    render_plan["background_video_query"] = preferred_query
    render_plan["background_video_path"] = normalized_path
    script_data.setdefault("metadata", {})["background_video_path"] = normalized_path


def prepare_assets(script_data: dict, style_id: str) -> None:
    render_plan = ensure_render_plan(script_data, style_id)
    attach_music(script_data, render_plan)
    attach_space_background(script_data, render_plan)
    attach_background_video(script_data, render_plan, style_id)


def expected_remotion_output(script_path: Path, style_id: str) -> Path:
    return VIDEOS_DIR / f"{script_path.stem}_{style_id}_remotion.mp4"


def expected_preview_output(script_path: Path) -> Path:
    return VIDEOS_DIR / f"{script_path.stem}_preview.mp4"


def expected_production_output(script_path: Path) -> Path:
    return VIDEOS_DIR / f"{script_path.stem}.mp4"


def run_remotion(script_path: Path, style_id: str, preview: bool) -> Path:
    npm_command = "npm.cmd" if os.name == "nt" else "npm"
    cmd = [npm_command, "run", "remotion:render", "--", str(script_path), "--style", style_id]
    if preview:
        cmd.append("--preview")
    subprocess.run(cmd, cwd=ROOT_DIR, check=True)
    output_path = expected_remotion_output(script_path, style_id)
    if not output_path.exists():
        raise FileNotFoundError(f"Expected Remotion output not found: {output_path}")
    return output_path


def run_python_renderer(script_path: Path, preview: bool) -> Path:
    cmd = [sys.executable, str(ROOT_DIR / "scripts" / "video_renderer.py")]
    if preview:
        cmd.append("--preview")
    subprocess.run(cmd, cwd=ROOT_DIR, check=True)
    target = expected_preview_output(script_path) if preview else expected_production_output(script_path)
    if not target.exists():
        raise FileNotFoundError(f"Expected Python renderer output not found: {target}")
    return target


def finalize_output(script_path: Path, rendered_path: Path, preview: bool) -> Path:
    target = expected_preview_output(script_path) if preview else expected_production_output(script_path)
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    if rendered_path.resolve() != target.resolve():
        shutil.copy2(rendered_path, target)
    return target


def update_script_metadata(script_path: Path, script_data: dict, output_path: Path, preview: bool, style_id: str) -> None:
    script_data["style_id"] = style_id
    render_plan = ensure_render_plan(script_data, style_id)
    normalized_output = repo_relative_path(output_path)
    render_plan["final_video_path"] = normalized_output

    if preview:
        script_data["preview_rendered_at"] = datetime.now().isoformat()
        script_data["preview_video_path"] = normalized_output
    else:
        script_data["rendered"] = True
        script_data["status"] = "rendered"
        script_data["rendered_at"] = datetime.now().isoformat()
        script_data["video_path"] = normalized_output
    save_script(script_path, script_data)


def main() -> None:
    args = parse_args()
    script_path = Path(args.script).resolve() if args.script else latest_script_path()
    if not script_path or not script_path.exists():
        raise SystemExit("No script JSON available to render.")

    script_data = load_script(script_path)
    style_id = selected_style_id(script_data, args.style)
    prepare_assets(script_data, style_id)
    save_script(script_path, script_data)

    print(f"Renderer orchestrator style: {style_id}")
    if use_remotion(style_id):
        rendered_path = run_remotion(script_path, style_id, preview=args.preview)
    else:
        rendered_path = run_python_renderer(script_path, preview=args.preview)

    final_path = finalize_output(script_path, rendered_path, preview=args.preview)
    update_script_metadata(script_path, script_data, final_path, preview=args.preview, style_id=style_id)
    print(final_path)


if __name__ == "__main__":
    main()
