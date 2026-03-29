"""
Style selection for Astro Shorts.

This module chooses a render style for a script, using analytics and recent usage
to keep the channel varied while biasing toward what performs best.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
STRATEGY_FILE = ROOT_DIR / "data" / "strategy.json"

STYLE_LIBRARY: dict[str, dict[str, str]] = {
    "planet_character": {
        "label": "Planet Character",
        "description": "Animated planet characters with expressive acting and cinematic cosmic motion.",
        "voice_mode": "off",
        "caption_font": "Montserrat ExtraBold",
        "background_mode": "nasa_space",
        "motion_profile": "cinematic_float",
        "music_style": "epic",
        "palette": "dark_cosmos",
        "render_template": "planet_character",
        "render_notes": "Use planets as the personality engine. Keep the motion smooth, bold, and emotionally readable.",
    },
    "educational_voiceless": {
        "label": "Educational Voiceless",
        "description": "Clean fact-first motion design with captions, diagrams, and no narration.",
        "voice_mode": "off",
        "caption_font": "Montserrat ExtraBold",
        "background_mode": "nasa_space",
        "motion_profile": "clean_infographic",
        "music_style": "cinematic",
        "palette": "navy_violet",
        "render_template": "educational_voiceless",
        "render_notes": "Prioritize clarity, spacing, and numbers. Keep movement elegant instead of chaotic.",
    },
    "character_explainer": {
        "label": "Character Explainer",
        "description": "Original host-character format over a dynamic gameplay-style backdrop with punchy captions.",
        "voice_mode": "narration_ready",
        "caption_font": "Montserrat ExtraBold",
        "background_mode": "gameplay",
        "motion_profile": "host_over_backdrop",
        "music_style": "upbeat_epic",
        "palette": "high_contrast",
        "render_template": "character_explainer",
        "render_notes": "Keep the host readable, energetic, and central. Use background motion for momentum, not distraction.",
    },
}

STYLE_TOPIC_PRIORS: dict[str, dict[str, float]] = {
    "planet_character": {
        "black_holes": 2.4,
        "scale_comparison": 2.6,
        "planets": 2.2,
        "extreme_physics": 1.7,
        "general": 1.1,
    },
    "educational_voiceless": {
        "travel_time": 2.6,
        "time": 2.4,
        "distances": 2.3,
        "extreme_physics": 1.8,
        "scale_comparison": 1.4,
        "general": 1.2,
    },
    "character_explainer": {
        "general": 2.4,
        "hypothetical": 2.2,
        "myth_busting": 2.0,
        "planets": 1.4,
        "scale_comparison": 1.1,
    },
}

STYLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "planet_character": ("planet", "earth", "jupiter", "saturn", "black hole", "singularity", "scale"),
    "educational_voiceless": ("travel", "distance", "time", "speed", "years", "light-year", "light speed"),
    "character_explainer": ("explainer", "story", "what if", "myth", "general", "teacher", "host"),
}

DEFAULT_STYLE_ID = "planet_character"


def load_strategy() -> dict:
    if STRATEGY_FILE.exists():
        try:
            return json.loads(STRATEGY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "style"


def infer_topic_family_from_text(text: str) -> str:
    normalized = text.lower()
    if any(term in normalized for term in ("black hole", "singularity", "event horizon")):
        return "black_holes"
    if any(term in normalized for term in ("travel", "distance", "speed", "light-year", "voyager")):
        return "travel_time"
    if any(term in normalized for term in ("time", "age", "future", "past", "dilation")):
        return "time"
    if any(term in normalized for term in ("planet", "earth", "mars", "jupiter", "saturn", "venus", "mercury")):
        return "planets"
    if any(term in normalized for term in ("what if", "hypothetical", "could", "would happen")):
        return "hypothetical"
    if any(term in normalized for term in ("myth", "true", "really", "actually", "fact")):
        return "myth_busting"
    if any(term in normalized for term in ("scale", "how many", "big", "largest", "compare")):
        return "scale_comparison"
    return "general"


def load_recent_styles(existing_ideas: list[dict], window: int = 12) -> list[str]:
    styles: list[str] = []
    for idea in existing_ideas[-window:]:
        if idea.get("status") not in {"pending", "formatted", "rendered", "uploaded"}:
            continue
        style_plan = idea.get("style_plan") or idea.get("render_style") or {}
        style_id = ""
        if isinstance(style_plan, dict):
            style_id = str(style_plan.get("style_id", "")).strip()
        elif isinstance(style_plan, str):
            style_id = style_plan.strip()
        if not style_id:
            style_id = str(idea.get("style_id", "")).strip()
        if style_id:
            styles.append(style_id)
    return styles


def _top_style_entries(strategy: dict) -> list[tuple[str, float]]:
    entries: list[tuple[str, float]] = []
    raw = strategy.get("top_performing_styles") or strategy.get("style_scores") or []
    if isinstance(raw, dict):
        for style_id, payload in raw.items():
            if isinstance(payload, dict):
                entries.append((str(style_id), float(payload.get("avg_score", 0.0))))
            else:
                entries.append((str(style_id), float(payload or 0.0)))
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                style_id = str(item.get("style_id") or item.get("style") or item.get("topic") or "").strip()
                score = float(item.get("avg_score", item.get("score", 0.0)) or 0.0)
                if style_id:
                    entries.append((style_id, score))
            elif isinstance(item, str):
                entries.append((item, 1.0))
    return entries


def _score_style(
    style_id: str,
    *,
    topic_family: str,
    topic_hint: str,
    strategy: dict,
    recent_styles: list[str],
) -> float:
    score = 0.0
    score += STYLE_TOPIC_PRIORS.get(style_id, {}).get(topic_family, 0.0)

    keyword_hits = 0.0
    text = topic_hint.lower()
    for term in STYLE_KEYWORDS.get(style_id, ()):
        if term in text:
            keyword_hits += 0.6
    score += keyword_hits

    for ranked_style, ranked_score in _top_style_entries(strategy):
        if ranked_style == style_id:
            score += 1.5 + ranked_score

    recent_penalty = sum(1 for recent in recent_styles[-4:] if recent == style_id)
    score -= recent_penalty * 0.7

    if style_id == DEFAULT_STYLE_ID and topic_family in {"black_holes", "scale_comparison", "planets"}:
        score += 0.4

    seed = hashlib.md5(f"{style_id}:{topic_family}:{topic_hint}".encode("utf-8")).hexdigest()
    score += (int(seed[:6], 16) % 13) / 100.0
    return round(score, 3)


def build_style_plan(
    style_id: str,
    *,
    topic_hint: str = "",
    topic_family: str = "general",
    strategy: dict | None = None,
    reason: str = "",
    selected_by: str = "heuristic",
) -> dict:
    strategy = strategy or load_strategy()
    base = STYLE_LIBRARY.get(style_id, STYLE_LIBRARY[DEFAULT_STYLE_ID]).copy()
    base.update(
        {
            "style_id": style_id if style_id in STYLE_LIBRARY else DEFAULT_STYLE_ID,
            "topic_hint": topic_hint,
            "topic_family": topic_family,
            "reason": reason,
            "selected_by": selected_by,
            "selected_at": datetime.now().isoformat(),
        }
    )
    base["music_style"] = base.get("music_style") or strategy.get("music_style") or "cinematic"
    return base


def select_style(
    *,
    strategy: dict | None = None,
    topic_hint: str = "",
    topic_family: str | None = None,
    existing_ideas: list[dict] | None = None,
    preferred_style: str | None = None,
) -> dict:
    strategy = strategy or load_strategy()
    existing_ideas = existing_ideas or []
    topic_family = topic_family or infer_topic_family_from_text(topic_hint)

    if preferred_style in STYLE_LIBRARY:
        return build_style_plan(
            preferred_style,
            topic_hint=topic_hint,
            topic_family=topic_family,
            strategy=strategy,
            reason="User override",
            selected_by="override",
        )

    recent_styles = load_recent_styles(existing_ideas)
    scores = {
        style_id: _score_style(
            style_id,
            topic_family=topic_family,
            topic_hint=topic_hint,
            strategy=strategy,
            recent_styles=recent_styles,
        )
        for style_id in STYLE_LIBRARY
    }
    chosen_style = max(scores, key=scores.get)
    top_score = scores[chosen_style]

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if len(ranked) > 1 and abs(ranked[0][1] - ranked[1][1]) <= 0.25:
        chosen_style = ranked[0][0] if recent_styles.count(ranked[0][0]) <= recent_styles.count(ranked[1][0]) else ranked[1][0]
        top_score = scores[chosen_style]

    family_reason = {
        "planet_character": "Planet character storytelling matched the topic's scale and visual impact.",
        "educational_voiceless": "Educational voiceless pacing fits fact-heavy, number-driven topics.",
        "character_explainer": "Character explainer style gives the most flexibility for narrative or mixed topics.",
    }.get(chosen_style, "Selected by style scoring.")

    return build_style_plan(
        chosen_style,
        topic_hint=topic_hint,
        topic_family=topic_family,
        strategy=strategy,
        reason=f"{family_reason} Score={top_score}",
        selected_by="analytics",
    ) | {"style_scores": scores, "ranking": ranked}


def style_prompt_fragment(style_plan: dict) -> str:
    style_id = style_plan.get("style_id", DEFAULT_STYLE_ID)
    style = STYLE_LIBRARY.get(style_id, STYLE_LIBRARY[DEFAULT_STYLE_ID])
    return (
        f"Style target: {style['label']}\n"
        f"Style brief: {style['description']}\n"
        f"Render notes: {style['render_notes']}\n"
        f"Caption font: {style['caption_font']}\n"
        f"Motion profile: {style['motion_profile']}\n"
        f"Background mode: {style['background_mode']}\n"
        f"Voice mode: {style['voice_mode']}\n"
        f"Music style: {style['music_style']}\n"
    )


def summarize_style_choices(strategy: dict | None = None) -> list[dict]:
    strategy = strategy or load_strategy()
    entries = _top_style_entries(strategy)
    if not entries:
        return [
            {"style_id": style_id, "label": data["label"], "score": 0.0}
            for style_id, data in STYLE_LIBRARY.items()
        ]
    return [
        {"style_id": style_id, "label": STYLE_LIBRARY.get(style_id, {}).get("label", style_id), "score": score}
        for style_id, score in sorted(entries, key=lambda item: item[1], reverse=True)
    ]
