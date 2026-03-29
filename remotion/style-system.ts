import type {AstroScriptData} from "./types";

export type RenderStyleId = "planet_character" | "educational_voiceless" | "character_explainer";
export type RenderStyleChoice = RenderStyleId | "auto";
export type BackgroundKind = "cosmic" | "clean" | "gameplay";

export type StyleConfig = {
  id: RenderStyleId;
  label: string;
  backgroundKind: BackgroundKind;
  captionPlacement: "top" | "bottom" | "split";
  fontFamily: string;
  accent: string;
  accentSecondary: string;
  accentTertiary: string;
  text: string;
  surface: string;
  surfaceStrong: string;
  glow: string;
  hookScale: number;
  captionScale: number;
  hostEnabled: boolean;
  emphasis: "cinematic" | "educational" | "energetic";
};

const FONT_STACK = 'Montserrat, "DejaVu Sans", system-ui, sans-serif';

export const STYLE_CONFIGS: Record<RenderStyleId, StyleConfig> = {
  planet_character: {
    id: "planet_character",
    label: "Planet Character",
    backgroundKind: "cosmic",
    captionPlacement: "top",
    fontFamily: FONT_STACK,
    accent: "#ffcf5a",
    accentSecondary: "#ff6bd6",
    accentTertiary: "#6ef3ff",
    text: "#ffffff",
    surface: "rgba(4, 8, 18, 0.76)",
    surfaceStrong: "rgba(7, 10, 24, 0.88)",
    glow: "rgba(255, 107, 214, 0.72)",
    hookScale: 1.08,
    captionScale: 1,
    hostEnabled: false,
    emphasis: "cinematic",
  },
  educational_voiceless: {
    id: "educational_voiceless",
    label: "Educational Voiceless",
    backgroundKind: "clean",
    captionPlacement: "top",
    fontFamily: FONT_STACK,
    accent: "#43f2c4",
    accentSecondary: "#94b8ff",
    accentTertiary: "#ffd54a",
    text: "#f6fbff",
    surface: "rgba(7, 14, 24, 0.80)",
    surfaceStrong: "rgba(8, 15, 29, 0.94)",
    glow: "rgba(67, 242, 196, 0.55)",
    hookScale: 0.98,
    captionScale: 0.95,
    hostEnabled: false,
    emphasis: "educational",
  },
  character_explainer: {
    id: "character_explainer",
    label: "Character Explainer",
    backgroundKind: "gameplay",
    captionPlacement: "bottom",
    fontFamily: FONT_STACK,
    accent: "#ffd54a",
    accentSecondary: "#70f0ff",
    accentTertiary: "#ff8bd1",
    text: "#ffffff",
    surface: "rgba(6, 8, 18, 0.70)",
    surfaceStrong: "rgba(8, 10, 22, 0.94)",
    glow: "rgba(112, 240, 255, 0.55)",
    hookScale: 1.0,
    captionScale: 1.05,
    hostEnabled: true,
    emphasis: "energetic",
  },
};

export function isRenderStyleId(value: unknown): value is RenderStyleId {
  return value === "planet_character" || value === "educational_voiceless" || value === "character_explainer";
}

export function isRenderStyleChoice(value: unknown): value is RenderStyleChoice {
  return value === "auto" || isRenderStyleId(value);
}

function normalizeText(value: unknown): string {
  return String(value ?? "").toLowerCase();
}

function styleFromText(scriptData: AstroScriptData): RenderStyleId {
  const idea = scriptData.idea ?? {};
  const metadata = scriptData.metadata ?? {};
  const text = [
    idea.topic,
    idea.title,
    idea.hook,
    metadata.mood,
    metadata.music_style,
    metadata.style_hint,
    metadata.background_mode,
    metadata.voice_emotion,
  ]
    .map(normalizeText)
    .join(" ");

  if (
    /black hole|singularity|event horizon|planet|solar system|sun|jupiter|saturn|galaxy|nebula|star|mystery|cosmic/.test(text)
  ) {
    return "planet_character";
  }

  if (
    /how many|how far|how long|scale|size|compare|distance|time|age|speed|weight|temperature|density|educational|explain|fact/.test(
      text,
    )
  ) {
    return "educational_voiceless";
  }

  if (/story|character|dialogue|brain rot|brainrot|meme|funny|chaos|relatable|saga/.test(text)) {
    return "character_explainer";
  }

  if (/epic|dramatic|intense|horror|mind-blowing|cinematic/.test(text)) {
    return "planet_character";
  }

  return "character_explainer";
}

export function resolveStyleId(scriptData: AstroScriptData, requestedStyle?: string): RenderStyleId {
  if (isRenderStyleId(requestedStyle)) {
    return requestedStyle;
  }

  const metadata = scriptData.metadata ?? {};
  const stylePlan = scriptData.style_plan ?? {};
  const renderPlan = scriptData.renderPlan ?? scriptData.render_plan ?? {};

  const directCandidates = [
    scriptData.style_id,
    stylePlan.style_id,
    renderPlan.selected_style_id,
    renderPlan.style_id,
    renderPlan.render_template,
    metadata.style_id,
    metadata.render_template,
    metadata.render_style,
    metadata.style_hint,
  ];

  for (const candidate of directCandidates) {
    if (isRenderStyleId(candidate)) {
      return candidate;
    }
  }

  return styleFromText(scriptData);
}

export function getStyleConfig(scriptData: AstroScriptData, requestedStyle?: string): StyleConfig {
  const resolved = resolveStyleId(scriptData, requestedStyle);
  return STYLE_CONFIGS[resolved];
}

export function compositionIdForStyle(styleId: RenderStyleChoice): string {
  if (styleId === "auto") {
    return "AstroShort";
  }
  return `AstroShort-${styleId.replace(/_/g, "-")}`;
}

export function styleLabel(styleId: RenderStyleChoice): string {
  if (styleId === "auto") {
    return "Auto";
  }
  return STYLE_CONFIGS[styleId].label;
}
