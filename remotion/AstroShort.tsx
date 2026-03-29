import React, {useMemo} from "react";
import {
  AbsoluteFill,
  Html5Audio,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type {AstroLayer, AstroScene, AstroRenderProps, AstroScriptData} from "./types";
import {getStyleConfig, type StyleConfig} from "./style-system";

const positions: Record<string, {x: number; y: number}> = {
  center: {x: 0.5, y: 0.54},
  left: {x: 0.26, y: 0.56},
  right: {x: 0.74, y: 0.56},
  top: {x: 0.5, y: 0.3},
  bottom: {x: 0.5, y: 0.76},
  bottom_left: {x: 0.28, y: 0.76},
  bottom_right: {x: 0.72, y: 0.76},
  top_left: {x: 0.28, y: 0.32},
  top_right: {x: 0.72, y: 0.32},
};

const sizes: Record<string, number> = {
  tiny: 90,
  small: 140,
  medium: 220,
  large: 320,
  huge: 430,
};

const planetStyles: Record<string, {base: string; accent: string; ring: string; face: string}> = {
  earth: {base: "#2e7ef7", accent: "#49c26a", ring: "rgba(80, 190, 122, 0.65)", face: "#10131e"},
  jupiter: {base: "#d9b182", accent: "#b56a44", ring: "rgba(181, 106, 68, 0.66)", face: "#281d17"},
  sun: {base: "#ffbf33", accent: "#ff7a00", ring: "rgba(255, 171, 41, 0.72)", face: "#331f00"},
  saturn: {base: "#ead29b", accent: "#c9a76f", ring: "rgba(237, 205, 142, 0.75)", face: "#2d2112"},
  mars: {base: "#df6b4d", accent: "#ffb08f", ring: "rgba(255, 126, 93, 0.72)", face: "#2b1510"},
  black_hole: {base: "#06060a", accent: "#ff7b38", ring: "rgba(255, 133, 66, 0.7)", face: "#050508"},
  moon: {base: "#bcc3cf", accent: "#7f8aa3", ring: "rgba(147, 160, 186, 0.62)", face: "#11131a"},
  default: {base: "#92a9ff", accent: "#71f2ff", ring: "rgba(113, 242, 255, 0.6)", face: "#10131d"},
};

const accentPalette = {
  text: "#ffffff",
  yellow: "#ffd54a",
  cyan: "#6ef3ff",
  magenta: "#ff69d4",
};

const backdropPalette: Record<StyleConfig["backgroundKind"], {base: string; mid: string; top: string}> = {
  cosmic: {base: "#03040a", mid: "#0b1128", top: "#23155f"},
  clean: {base: "#050811", mid: "#08111f", top: "#0d172b"},
  gameplay: {base: "#04060d", mid: "#102338", top: "#64c8ff"},
};

const clamp = (value: number, low: number, high: number) => Math.max(low, Math.min(high, value));

const hashText = (text: string): number => {
  let hash = 2166136261;
  for (let index = 0; index < text.length; index++) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
};

function mulberry32(seed: number): () => number {
  return () => {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function easeOutBack(value: number) {
  const t = clamp(value, 0, 1);
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
}

function getDuration(data: AstroScriptData, fps: number) {
  const scenes = data.timeline ?? [];
  const maxSceneEnd = scenes.length ? Math.max(...scenes.map((scene) => scene.time_end ?? 0)) : 0;
  const totalSeconds = Math.max(maxSceneEnd, 12) + 1.4;
  return Math.ceil(totalSeconds * fps);
}

function getSceneAtTime(scenes: AstroScene[], seconds: number) {
  return scenes.find((scene) => seconds >= (scene.time_start ?? 0) && seconds < (scene.time_end ?? 0)) ?? scenes[0];
}

function isPlanetWord(word: string) {
  const clean = word.toLowerCase().replace(/[^\w]/g, "");
  return ["earth", "sun", "jupiter", "saturn", "mars", "moon", "neptune", "venus", "mercury", "blackhole", "black_hole"].includes(clean);
}

function wrapText(content: string, maxChars: number, maxLines: number) {
  const words = content.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > maxChars && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
    if (lines.length >= maxLines) {
      break;
    }
  }

  if (lines.length < maxLines && current) {
    lines.push(current);
  }

  if (lines.length > maxLines) {
    lines.length = maxLines;
  }

  const consumed = lines.join(" ").trim();
  if (consumed.length < content.trim().length && lines.length > 0) {
    lines[lines.length - 1] = `${lines[lines.length - 1]}...`;
  }

  return lines;
}

function tokenizeText(content: string) {
  return content.split(/\s+/).filter(Boolean).map((word, index) => {
    const clean = word.toLowerCase().replace(/[^\w]/g, "");
    const isNumber = /\d/.test(word);
    const isPlanet = isPlanetWord(word);
    const isCaps = word.length > 2 && word === word.toUpperCase();

    return {
      key: `${clean}-${index}`,
      word,
      color: isNumber ? accentPalette.yellow : isPlanet ? accentPalette.cyan : isCaps ? accentPalette.magenta : accentPalette.text,
      scale: isNumber ? 1.2 : isPlanet ? 1.08 : 1,
      glow: isNumber || isPlanet || isCaps,
    };
  });
}

function normalizeAssetSrc(assetSrc?: string) {
  if (!assetSrc) {
    return null;
  }

  if (/^https?:\/\//i.test(assetSrc) || /^data:/i.test(assetSrc)) {
    return assetSrc;
  }

  const normalized = assetSrc.replace(/\\/g, "/").replace(/^\/+/, "");
  return staticFile(normalized);
}

const Starfield: React.FC<{style: StyleConfig; time: number}> = ({style, time}) => {
  const stars = useMemo(() => {
    const rand = mulberry32(hashText(`${style.id}:${style.backgroundKind}`));
    const count = style.backgroundKind === "gameplay" ? 70 : style.backgroundKind === "clean" ? 52 : 94;
    return new Array(count).fill(true).map((_, i) => ({
      left: `${rand() * 100}%`,
      top: `${rand() * 100}%`,
      size: 1 + (i % 4),
      opacity: 0.14 + rand() * 0.56,
      driftX: (rand() - 0.5) * (style.backgroundKind === "cosmic" ? 20 : 12),
      driftY: (rand() - 0.5) * (style.backgroundKind === "cosmic" ? 14 : 10),
      phase: rand() * Math.PI * 2,
    }));
  }, [style.backgroundKind, style.id]);

  return (
    <>
      {stars.map((star, index) => (
        <div
          key={index}
          style={{
            position: "absolute",
            left: star.left,
            top: star.top,
            width: star.size,
            height: star.size,
            borderRadius: 999,
            background: "white",
            opacity: star.opacity,
            transform: `translate(${Math.sin(time * 0.25 + star.phase) * star.driftX}px, ${Math.cos(time * 0.18 + star.phase) * star.driftY}px)`,
            boxShadow: "0 0 10px rgba(255,255,255,0.7)",
          }}
        />
      ))}
    </>
  );
};

const NebulaBlobs: React.FC<{style: StyleConfig; time: number}> = ({style, time}) => {
  const blobs = style.backgroundKind === "clean" ? 2 : 3;
  const tint = style.backgroundKind === "gameplay" ? style.accentSecondary : style.accent;

  return (
    <>
      {new Array(blobs).fill(true).map((_, index) => {
        const left = [18, 70, 52][index] ?? 50;
        const top = [18, 26, 66][index] ?? 40;
        const scale = [1.15, 1.0, 1.25][index] ?? 1;
        const phase = index * 1.7;
        const opacity = 0.14 + Math.sin(time * 0.7 + phase) * 0.04;

        return (
          <div
            key={index}
            style={{
              position: "absolute",
              left: `${left}%`,
              top: `${top}%`,
              width: 430 * scale,
              height: 260 * scale,
              marginLeft: -215 * scale,
              marginTop: -130 * scale,
              borderRadius: "50%",
              background: `radial-gradient(circle, ${tint}33 0%, ${tint}18 38%, transparent 72%)`,
              filter: "blur(22px)",
              opacity,
              transform: `translate(${Math.sin(time * 0.15 + phase) * 16}px, ${Math.cos(time * 0.12 + phase) * 12}px)`,
            }}
          />
        );
      })}
    </>
  );
};

const ShootingStar: React.FC<{style: StyleConfig; time: number; durationSeconds: number}> = ({style, time, durationSeconds}) => {
  const seed = hashText(`${style.id}:${durationSeconds.toFixed(2)}`);
  const rand = mulberry32(seed);
  const start = Math.max(0.6, durationSeconds * (0.3 + rand() * 0.4));
  const lifespan = 0.9 + rand() * 0.65;
  const progress = (time - start) / lifespan;

  if (progress < 0 || progress > 1) {
    return null;
  }

  const x = 0.72 - progress * 0.48;
  const y = 0.18 + progress * 0.34;

  return (
    <div
      style={{
        position: "absolute",
        left: `${x * 100}%`,
        top: `${y * 100}%`,
        width: 260,
        height: 3,
        transform: `rotate(-22deg) scale(${1 - progress * 0.15})`,
        transformOrigin: "left center",
        background: `linear-gradient(90deg, transparent, ${style.accentSecondary}, white)`,
        opacity: 1 - Math.abs(progress - 0.5) * 1.25,
        boxShadow: `0 0 20px ${style.accentSecondary}`,
      }}
    />
  );
};

const BackdropGrid: React.FC<{style: StyleConfig; time: number}> = ({style, time}) => {
  if (style.backgroundKind === "cosmic") {
    return null;
  }

  const lineOpacity = style.backgroundKind === "gameplay" ? 0.16 : 0.08;
  const offset = Math.sin(time * 0.12) * 18;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundImage:
          "linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)",
        backgroundSize: style.backgroundKind === "gameplay" ? "90px 90px" : "120px 120px",
        maskImage: "linear-gradient(to bottom, rgba(0,0,0,0.7), transparent 80%)",
        opacity: lineOpacity,
        transform: `translateY(${offset}px)`,
      }}
    />
  );
};
const PlanetCharacter: React.FC<{layer: AstroLayer; time: number; style: StyleConfig}> = ({layer, time, style}) => {
  const pos = positions[layer.position ?? "center"] ?? positions.center;
  const size = sizes[layer.size ?? "medium"] ?? sizes.medium;
  const palette = planetStyles[layer.name ?? "default"] ?? planetStyles.default;
  const seed = hashText(`${style.id}:${layer.name ?? "planet"}`);
  const name = (layer.name ?? "earth").toLowerCase();
  const isBlackHole = name === "black_hole" || name === "blackhole";
  const isSun = name === "sun";
  const isSaturn = name === "saturn";
  const baseDrift = style.id === "character_explainer" ? 0.86 : style.id === "educational_voiceless" ? 0.58 : 1;
  const bounceY = Math.sin(time * 1.7 + pos.x * 3 + seed * 0.00001) * (18 * baseDrift);
  const swayX = Math.sin(time * 0.95 + pos.y * 4 + seed * 0.00001) * (10 * baseDrift);
  const pulse = 1 + Math.sin(time * 2.8 + seed * 0.00002) * (layer.effects?.includes("pulse") ? 0.05 : 0.02);
  const blink = Math.abs(Math.sin(time * (style.id === "character_explainer" ? 2.2 : 1.7) + seed * 0.00003)) > 0.95;
  const gaze = Math.sin(time * 0.8 + seed * 0.00005) * (style.id === "educational_voiceless" ? 2.5 : 4);
  const mouthSmile = Math.sin(time * 1.1 + pos.x * 5) * 2;

  return (
    <div
      style={{
        position: "absolute",
        left: `calc(${pos.x * 100}% - ${size / 2}px)`,
        top: `calc(${pos.y * 100}% - ${size / 2}px)`,
        width: size,
        height: size,
        transform: `translate(${swayX}px, ${bounceY}px) scale(${pulse})`,
        filter: `drop-shadow(0 0 ${style.id === "planet_character" ? 48 : 32}px ${palette.ring})`,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: -size * 0.12,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${palette.accent}44 0%, transparent 70%)`,
          filter: "blur(16px)",
          opacity: 0.75,
        }}
      />
      {isBlackHole ? (
        <>
          <div
            style={{
              position: "absolute",
              inset: size * 0.22,
              borderRadius: "50%",
              background: "radial-gradient(circle, #000000 0%, #050505 45%, #111 100%)",
              boxShadow: `0 0 40px ${palette.accent}99`,
            }}
          />
          <div
            style={{
              position: "absolute",
              left: -size * 0.04,
              top: size * 0.34,
              width: size * 1.08,
              height: size * 0.28,
              borderRadius: "50%",
              background:
                "linear-gradient(90deg, rgba(255,90,60,0.12), rgba(255,178,57,0.7), rgba(255,238,118,0.85), rgba(255,178,57,0.7), rgba(255,90,60,0.12))",
              transform: `rotate(-14deg) scaleY(0.55)`,
              filter: "blur(1px)",
              opacity: 0.9,
            }}
          />
          <div
            style={{
              position: "absolute",
              left: size * 0.24,
              top: size * 0.34,
              width: size * 0.52,
              height: size * 0.32,
              borderRadius: "50%",
              background: "radial-gradient(circle, rgba(255,255,255,0.7) 0%, rgba(255,132,63,0.45) 30%, transparent 70%)",
              mixBlendMode: "screen",
              filter: "blur(8px)",
              opacity: 0.7,
            }}
          />
        </>
      ) : (
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            background: `radial-gradient(circle at 28% 24%, rgba(255,255,255,0.92) 0%, ${palette.base} 28%, ${palette.accent} 110%)`,
            boxShadow: `inset -18px -24px 44px rgba(0,0,0,0.24), 0 0 34px ${palette.ring}`,
            overflow: "hidden",
          }}
        >
          {isSaturn ? (
            <>
              <div
                style={{
                  position: "absolute",
                  left: -size * 0.16,
                  top: size * 0.35,
                  width: size * 1.32,
                  height: size * 0.26,
                  borderRadius: "50%",
                  border: `9px solid ${palette.ring}`,
                  transform: "rotate(-12deg)",
                  opacity: 0.9,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: -size * 0.12,
                  top: size * 0.41,
                  width: size * 1.24,
                  height: size * 0.18,
                  borderRadius: "50%",
                  border: "6px solid rgba(255,255,255,0.12)",
                  transform: "rotate(-12deg)",
                }}
              />
            </>
          ) : null}
          {isSun ? (
            <div style={{position: "absolute", inset: 0, borderRadius: "50%"}}>
              {new Array(8).fill(true).map((_, index) => {
                const angle = (Math.PI * 2 * index) / 8 + time * 0.4;
                const rayLength = size * 0.34 + Math.sin(time * 1.2 + index) * 6;
                return (
                  <div
                    key={index}
                    style={{
                      position: "absolute",
                      left: "50%",
                      top: "50%",
                      width: 8,
                      height: rayLength,
                      background: `linear-gradient(180deg, ${palette.accent}cc, transparent)`,
                      transformOrigin: "center top",
                      transform: `translate(-50%, -92%) rotate(${angle}rad)`,
                      opacity: 0.55 + Math.sin(time * 1.5 + index) * 0.18,
                      borderRadius: 999,
                      filter: "blur(1px)",
                    }}
                  />
                );
              })}
            </div>
          ) : null}
          <div
            style={{
              position: "absolute",
              left: size * 0.2,
              top: size * 0.28,
              width: size * 0.16,
              height: blink ? size * 0.02 : size * 0.18,
              borderRadius: 999,
              background: "white",
              border: "4px solid #0a0a0f",
              transform: `translateX(${gaze}px)`,
            }}
          >
            {!blink ? (
              <div
                style={{
                  position: "absolute",
                  left: "50%",
                  top: "50%",
                  width: size * 0.07,
                  height: size * 0.07,
                  borderRadius: "50%",
                  background: "#101010",
                  transform: `translate(calc(-50% + ${gaze}px), -50%)`,
                }}
              />
            ) : null}
          </div>
          <div
            style={{
              position: "absolute",
              right: size * 0.2,
              top: size * 0.28,
              width: size * 0.16,
              height: blink ? size * 0.02 : size * 0.18,
              borderRadius: 999,
              background: "white",
              border: "4px solid #0a0a0f",
              transform: `translateX(${gaze}px)`,
            }}
          >
            {!blink ? (
              <div
                style={{
                  position: "absolute",
                  left: "50%",
                  top: "50%",
                  width: size * 0.07,
                  height: size * 0.07,
                  borderRadius: "50%",
                  background: "#101010",
                  transform: `translate(calc(-50% + ${gaze}px), -50%)`,
                }}
              />
            ) : null}
          </div>
          <div
            style={{
              position: "absolute",
              left: "50%",
              bottom: size * 0.18,
              width: size * 0.24,
              height: size * 0.12,
              transform: `translateX(-50%) translateY(${mouthSmile * 0.3}px)`,
              borderBottom: `6px solid ${palette.face}`,
              borderRadius: "0 0 999px 999px",
            }}
          />
          <div
            style={{
              position: "absolute",
              left: size * 0.18,
              top: size * 0.44,
              width: size * 0.08,
              height: size * 0.04,
              borderRadius: 999,
              background: "rgba(255,255,255,0.18)",
              opacity: 0.65,
            }}
          />
          <div
            style={{
              position: "absolute",
              right: size * 0.18,
              top: size * 0.44,
              width: size * 0.08,
              height: size * 0.04,
              borderRadius: 999,
              background: "rgba(255,255,255,0.18)",
              opacity: 0.65,
            }}
          />
        </div>
      )}
    </div>
  );
};
const CaptionPanel: React.FC<{
  scene: AstroScene | undefined;
  progress: number;
  style: StyleConfig;
  fps: number;
}> = ({scene, progress, style, fps}) => {
  const content = scene?.text?.content ?? "";
  if (!content) {
    return null;
  }

  const lines =
    style.id === "educational_voiceless"
      ? wrapText(content, 26, 4)
      : style.id === "character_explainer"
        ? wrapText(content, 22, 3)
        : wrapText(content, 18, 4);
  const enter = spring({
    fps,
    frame: Math.floor(progress * fps),
    config: {damping: 180, stiffness: 120},
  });
  const scale = easeOutBack(interpolate(enter, [0, 1], [0.88, 1]));
  const offsetY = style.captionPlacement === "bottom" ? 0 : -6;
  const anchorStyles =
    style.id === "character_explainer"
      ? {
          bottom: 128,
          left: 54,
          right: 54,
          alignItems: "stretch",
        }
      : style.captionPlacement === "bottom"
        ? {
            bottom: 170,
            left: 52,
            right: 52,
            alignItems: "center",
          }
        : {
            top: 126,
            left: 58,
            right: 58,
            alignItems: "flex-start",
          };

  return (
    <div
      style={{
        position: "absolute",
        display: "flex",
        flexDirection: "column",
        gap: 14,
        transform: `translateY(${offsetY}px) scale(${scale})`,
        ...anchorStyles,
      }}
    >
      <div
        style={{
          alignSelf: style.id === "character_explainer" ? "flex-start" : "auto",
          padding: "9px 14px",
          borderRadius: 999,
          background: style.surfaceStrong,
          border: `1px solid ${style.accent}44`,
          color: style.accent,
          fontFamily: style.fontFamily,
          fontSize: style.id === "educational_voiceless" ? 18 : 20,
          fontWeight: 900,
          letterSpacing: 1.6,
          textTransform: "uppercase",
          boxShadow: `0 0 24px ${style.glow}22`,
          width: "fit-content",
        }}
      >
        {style.id === "character_explainer" ? "Character Explainer" : style.id === "educational_voiceless" ? "Educational" : "Planet Character"}
      </div>
      <div
        style={{
          display: "flex",
          gap: 18,
          alignItems: "stretch",
          padding: style.id === "character_explainer" ? 18 : 0,
          borderRadius: style.id === "character_explainer" ? 32 : 0,
          background: style.id === "character_explainer" ? "rgba(4, 8, 18, 0.55)" : "transparent",
          width: "fit-content",
          maxWidth: "100%",
        }}
      >
        {style.id === "character_explainer" ? (
          <div
            style={{
              width: 124,
              minWidth: 124,
              borderRadius: 28,
              background:
                "radial-gradient(circle at 35% 28%, rgba(255,255,255,0.18), transparent 34%), linear-gradient(180deg, rgba(29,37,72,0.92), rgba(8,10,20,0.96))",
              border: "1px solid rgba(255,255,255,0.1)",
              boxShadow: "0 18px 48px rgba(0,0,0,0.35)",
              position: "relative",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: 18,
                borderRadius: "50%",
                background: `radial-gradient(circle at 35% 30%, #ffffff 0%, ${style.accent} 25%, rgba(11,14,24,0.95) 84%)`,
                boxShadow: `0 0 28px ${style.accent}55`,
              }}
            />
            <div
              style={{
                position: "absolute",
                left: 34,
                top: 42,
                width: 14,
                height: 22,
                borderRadius: 999,
                background: "#111",
                boxShadow: "36px 0 0 #111",
              }}
            />
            <div
              style={{
                position: "absolute",
                left: 46,
                bottom: 28,
                width: 32,
                height: 14,
                borderBottom: "5px solid #101010",
                borderRadius: "0 0 999px 999px",
              }}
            />
          </div>
        ) : null}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            flex: 1,
            padding: style.id === "character_explainer" ? 6 : 0,
          }}
        >
          {lines.map((line, lineIndex) => (
            <div
              key={lineIndex}
              style={{
                display: "inline-block",
                width: "fit-content",
                padding: style.id === "educational_voiceless" ? "12px 18px" : "12px 20px",
                borderRadius: 24,
                background: style.surface,
                border: `1px solid ${style.accent}28`,
                boxShadow: `0 10px 36px rgba(0,0,0,0.34)`,
                color: style.text,
                fontFamily: style.fontFamily,
                fontWeight: 900,
                fontSize: style.id === "educational_voiceless" ? 46 : style.id === "character_explainer" ? 54 : 62,
                lineHeight: 1.06,
                maxWidth: style.id === "character_explainer" ? 880 : 920,
              }}
            >
              {tokenizeText(line).map((token) => (
                <span
                  key={token.key}
                  style={{
                    color: token.color,
                    fontSize: `${token.scale}em`,
                    marginRight: 10,
                    textShadow: token.glow ? `0 0 14px ${token.color}66` : "0 0 10px rgba(255,255,255,0.14)",
                  }}
                >
                  {token.word}
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const SceneEffects: React.FC<{
  scene: AstroScene | undefined;
  style: StyleConfig;
  fps: number;
  sceneFrame: number;
}> = ({scene, style, fps, sceneFrame}) => {
  const effects = scene?.screen_effects ?? [];
  const dramatic = Boolean(scene?.dramatic_moment);
  const flash = dramatic || effects.includes("flash") || effects.includes("energy_burst");
  const shake = effects.includes("shake") || (style.id === "character_explainer" && effects.includes("speed_lines"));
  const scanlines = style.id === "educational_voiceless" || effects.includes("scanlines");
  const pulse = interpolate(sceneFrame, [0, fps * 0.8], [1, 0], {extrapolateRight: "clamp"});

  return (
    <>
      {flash ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "white",
            opacity: pulse * 0.22,
            mixBlendMode: "screen",
          }}
        />
      ) : null}
      {shake ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            transform: `translate(${Math.sin(sceneFrame * 0.7) * 3}px, ${Math.cos(sceneFrame * 0.6) * 2}px)`,
          }}
        />
      ) : null}
      {scanlines ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: "linear-gradient(to bottom, rgba(255,255,255,0.04) 0, rgba(255,255,255,0.04) 1px, transparent 1px, transparent 8px)",
            backgroundSize: "100% 8px",
            opacity: style.id === "educational_voiceless" ? 0.08 : 0.04,
            mixBlendMode: "soft-light",
          }}
        />
      ) : null}
    </>
  );
};

const HookScene: React.FC<{
  scriptData: AstroScriptData;
  style: StyleConfig;
  frame: number;
  hookLength: number;
}> = ({scriptData, style, frame, hookLength}) => {
  const hookText = scriptData.idea?.hook ?? scriptData.idea?.title ?? "SPACE FACTS";
  const hookEnter = interpolate(frame, [0, hookLength * 30], [0.6, 1], {extrapolateRight: "clamp"});
  const scale = easeOutBack(hookEnter);
  const underline = interpolate(frame, [0, 12], [0, 1], {extrapolateRight: "clamp"});
  const lines = style.id === "educational_voiceless" ? wrapText(hookText, 22, 3) : wrapText(hookText, 16, 3);

  return (
    <div
      style={{
        position: "absolute",
        left: style.id === "character_explainer" ? 58 : 68,
        right: style.id === "character_explainer" ? 58 : 68,
        top: style.id === "character_explainer" ? 188 : 250,
        transform: `scale(${scale})`,
        transformOrigin: "top left",
        color: style.text,
        fontFamily: style.fontFamily,
      }}
    >
      <div
        style={{
          display: "inline-flex",
          padding: "10px 16px",
          borderRadius: 999,
          background: style.surfaceStrong,
          border: `1px solid ${style.accent}55`,
          color: style.accent,
          fontSize: 20,
          fontWeight: 900,
          letterSpacing: 1.8,
          textTransform: "uppercase",
          boxShadow: `0 0 24px ${style.glow}22`,
        }}
      >
        {style.id === "character_explainer" ? "Character Explainer" : style.id === "educational_voiceless" ? "Educational" : "Planet Character"}
      </div>
      <div
        style={{
          marginTop: 22,
          display: "flex",
          flexDirection: "column",
          gap: 14,
          maxWidth: style.id === "character_explainer" ? 880 : 900,
        }}
      >
        {lines.map((line, lineIndex) => (
          <div
            key={lineIndex}
            style={{
              display: "inline-block",
              width: "fit-content",
              padding: "16px 22px",
              borderRadius: 28,
              background: style.surface,
              border: `1px solid ${style.accent}22`,
              boxShadow: "0 16px 40px rgba(0,0,0,0.36)",
              fontWeight: 900,
              fontSize: style.id === "educational_voiceless" ? 58 : 72,
              lineHeight: 1.02,
            }}
          >
            {tokenizeText(line).map((token) => (
              <span
                key={token.key}
                style={{
                  color: token.color,
                  fontSize: `${token.scale}em`,
                  marginRight: 12,
                  textShadow: token.glow ? `0 0 16px ${token.color}55` : "0 0 12px rgba(255,255,255,0.15)",
                }}
              >
                {token.word}
              </span>
            ))}
          </div>
        ))}
      </div>
      <div
        style={{
          marginTop: 24,
          width: `${Math.max(36, underline * 100)}%`,
          height: 8,
          borderRadius: 999,
          background: `linear-gradient(90deg, ${style.accent}, ${style.accentSecondary})`,
          boxShadow: `0 0 20px ${style.glow}`,
        }}
      />
    </div>
  );
};

const BackgroundVideoLayer: React.FC<{src: string}> = ({src}) => {
  return (
    <video
      src={src}
      autoPlay
      muted
      loop
      playsInline
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        objectFit: "cover",
        opacity: 0.58,
        filter: "saturate(1.08) brightness(0.72) contrast(1.08)",
      }}
    />
  );
};

const BackgroundImageLayer: React.FC<{src: string; style: StyleConfig; time: number}> = ({src, style, time}) => {
  const scale = 1.04 + Math.sin(time * 0.12) * 0.015;
  const translateX = Math.sin(time * 0.08) * 18;
  const translateY = Math.cos(time * 0.06) * 12;
  const opacity = style.id === "character_explainer" ? 0.28 : style.id === "educational_voiceless" ? 0.34 : 0.38;

  return (
    <img
      src={src}
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        objectFit: "cover",
        opacity,
        transform: `translate(${translateX}px, ${translateY}px) scale(${scale})`,
        filter: "brightness(0.34) saturate(1.05) contrast(1.04)",
      }}
    />
  );
};

export const AstroShortComposition: React.FC<AstroRenderProps> = ({
  scriptData,
  styleId,
  backgroundVideoSrc,
  backgroundImageSrc,
  musicSrc,
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const seconds = frame / fps;
  const style = getStyleConfig(scriptData, styleId);
  const hookLength = style.id === "planet_character" ? 2.2 : style.id === "educational_voiceless" ? 2.0 : 2.15;
  const scenes = scriptData.timeline ?? [];
  const activeScene = seconds < hookLength ? undefined : getSceneAtTime(scenes, seconds - hookLength);
  const sceneProgress =
    activeScene == null
      ? Math.min(seconds / hookLength, 1)
      : (seconds - hookLength - (activeScene.time_start ?? 0)) / Math.max((activeScene.time_end ?? 4) - (activeScene.time_start ?? 0), 0.01);
  const globalProgress = frame / durationInFrames;
  const sceneFrame = Math.max(0, (seconds - hookLength - (activeScene?.time_start ?? 0)) * fps);
  const resolvedBackgroundVideoSrc = style.id === "character_explainer" ? normalizeAssetSrc(backgroundVideoSrc) : null;
  const resolvedBackgroundImageSrc = normalizeAssetSrc(backgroundImageSrc);
  const resolvedMusicSrc = normalizeAssetSrc(musicSrc);
  const background = backdropPalette[style.backgroundKind];

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at top, ${background.top} 0%, ${background.mid} 46%, ${background.base} 100%)`,
        overflow: "hidden",
        fontFamily: style.fontFamily,
      }}
    >
      {resolvedMusicSrc ? <Html5Audio src={resolvedMusicSrc} volume={style.id === "character_explainer" ? 0.34 : 0.28} /> : null}
      {resolvedBackgroundImageSrc ? <BackgroundImageLayer src={resolvedBackgroundImageSrc} style={style} time={seconds} /> : null}
      {style.id === "character_explainer" && resolvedBackgroundVideoSrc ? <BackgroundVideoLayer src={resolvedBackgroundVideoSrc} /> : null}
      <AbsoluteFill
        style={{
          background:
            style.id === "planet_character"
              ? "radial-gradient(circle at 18% 20%, rgba(146,98,255,0.34), transparent 32%), radial-gradient(circle at 82% 68%, rgba(255,97,190,0.24), transparent 28%), radial-gradient(circle at 52% 42%, rgba(58,151,255,0.18), transparent 34%)"
              : style.id === "educational_voiceless"
                ? "radial-gradient(circle at 16% 18%, rgba(67,242,196,0.20), transparent 28%), radial-gradient(circle at 82% 22%, rgba(148,184,255,0.22), transparent 30%), radial-gradient(circle at 50% 52%, rgba(255,213,74,0.08), transparent 36%)"
                : "radial-gradient(circle at 12% 18%, rgba(255,213,74,0.18), transparent 28%), radial-gradient(circle at 82% 16%, rgba(255,107,214,0.20), transparent 26%), radial-gradient(circle at 48% 54%, rgba(112,240,255,0.12), transparent 34%)",
        }}
      />
      <NebulaBlobs style={style} time={seconds} />
      <Starfield style={style} time={seconds} />
      <BackdropGrid style={style} time={seconds} />
      <ShootingStar style={style} time={seconds} durationSeconds={durationInFrames / fps} />

      {seconds < hookLength ? (
        <HookScene scriptData={scriptData} style={style} frame={frame} hookLength={hookLength} />
      ) : (
        <>
          {style.id === "character_explainer" ? (
            <div
              style={{
                position: "absolute",
                left: 50,
                right: 50,
                top: 150,
                bottom: 160,
                borderRadius: 42,
                border: "1px solid rgba(255,255,255,0.08)",
                background: "rgba(4, 8, 18, 0.22)",
                boxShadow: "0 22px 60px rgba(0,0,0,0.28)",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background:
                    "linear-gradient(90deg, rgba(10,14,28,0.74) 0%, rgba(10,14,28,0.38) 36%, rgba(10,14,28,0.74) 100%)",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  left: 30,
                  top: 28,
                  padding: "8px 14px",
                  borderRadius: 999,
                  background: "rgba(0,0,0,0.45)",
                  color: style.accent,
                  fontSize: 18,
                  fontWeight: 900,
                  letterSpacing: 1.4,
                  textTransform: "uppercase",
                  border: "1px solid rgba(255,255,255,0.08)",
                }}
              >
                Gameplay style overlay
              </div>
            </div>
          ) : null}
          {activeScene?.layers
            ?.filter((layer: AstroLayer) => layer.type === "planet")
            .map((layer: AstroLayer, index: number) => (
              <PlanetCharacter key={`${layer.name}-${index}`} layer={layer} time={seconds} style={style} />
            ))}
          <CaptionPanel scene={activeScene} progress={sceneProgress} style={style} fps={fps} />
          <SceneEffects scene={activeScene} style={style} fps={fps} sceneFrame={sceneFrame} />
        </>
      )}

      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          height: style.id === "educational_voiceless" ? 8 : 10,
          width: `${globalProgress * 100}%`,
          background: `linear-gradient(90deg, ${style.accent}, ${style.accentSecondary})`,
          boxShadow: `0 0 18px ${style.glow}`,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: `calc(${globalProgress * 100}% - 4px)`,
          width: 8,
          height: style.id === "educational_voiceless" ? 10 : 12,
          borderRadius: 999,
          background: "white",
          boxShadow: `0 0 22px ${style.accentSecondary}, 0 0 40px ${style.accentSecondary}`,
        }}
      />
    </AbsoluteFill>
  );
};

export const astroShortDuration = (data: AstroScriptData) => getDuration(data, 30);

export const AstroShortRemotionRoot: React.FC<{
  scriptData: AstroScriptData;
  styleId?: string;
  backgroundVideoSrc?: string;
  backgroundImageSrc?: string;
  musicSrc?: string;
}> = ({
  scriptData,
  styleId,
  backgroundVideoSrc,
  backgroundImageSrc,
  musicSrc,
}) => {
  return (
    <AstroShortComposition
      scriptData={scriptData}
      styleId={styleId}
      backgroundVideoSrc={backgroundVideoSrc}
      backgroundImageSrc={backgroundImageSrc}
      musicSrc={musicSrc}
    />
  );
};
