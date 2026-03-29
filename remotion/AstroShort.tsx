import React, {useMemo} from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import type {AstroLayer, AstroScene, AstroScriptData} from "./types";

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

const planetStyles: Record<string, {base: string; accent: string}> = {
  earth: {base: "#2e7ef7", accent: "#49c26a"},
  jupiter: {base: "#d9b182", accent: "#b56a44"},
  sun: {base: "#ffbf33", accent: "#ff7a00"},
  saturn: {base: "#ead29b", accent: "#c9a76f"},
  mars: {base: "#df6b4d", accent: "#ffb08f"},
  black_hole: {base: "#07070b", accent: "#ff7b38"},
};

const accentPalette = {
  text: "#ffffff",
  yellow: "#ffd54a",
  cyan: "#6ef3ff",
  magenta: "#ff69d4",
};

const getDuration = (data: AstroScriptData, fps: number) => {
  const scenes = data.timeline ?? [];
  const totalSeconds = Math.max(...scenes.map((scene: AstroScene) => scene.time_end ?? 0), 12) + 1.4;
  return Math.ceil(totalSeconds * fps);
};

const getSceneAtTime = (scenes: AstroScene[], seconds: number) => {
  return scenes.find((scene) => seconds >= (scene.time_start ?? 0) && seconds < (scene.time_end ?? 0)) ?? scenes[0];
};

const splitText = (content: string) => {
  const words = content.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > 18 && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) {
    lines.push(current);
  }
  return lines.slice(0, 5);
};

const Starfield: React.FC = () => {
  const stars = useMemo(
    () =>
      new Array(80).fill(true).map((_, i) => ({
        left: `${(i * 13) % 100}%`,
        top: `${(i * 29) % 100}%`,
        size: 1 + (i % 3),
        opacity: 0.25 + ((i * 7) % 10) / 14,
      })),
    [],
  );

  return (
    <>
      {stars.map((star, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: star.left,
            top: star.top,
            width: star.size,
            height: star.size,
            borderRadius: 999,
            background: "white",
            opacity: star.opacity,
            boxShadow: "0 0 8px rgba(255,255,255,0.6)",
          }}
        />
      ))}
    </>
  );
};

const PlanetCharacter: React.FC<{layer: AstroLayer; time: number}> = ({layer, time}) => {
  const pos = positions[layer.position ?? "center"] ?? positions.center;
  const size = sizes[layer.size ?? "medium"] ?? sizes.medium;
  const palette = planetStyles[layer.name ?? "earth"] ?? planetStyles.earth;
  const bounce = Math.sin(time * 2.2 + pos.x * 4) * 18;
  const sway = Math.sin(time * 1.1 + pos.y * 3) * 10;
  const pulse = layer.effects?.includes("pulse") ? 1 + Math.sin(time * 3.8) * 0.03 : 1;
  const blink = Math.abs(Math.sin(time * 1.7 + pos.x * 8)) > 0.94;
  const pupilShift = Math.sin(time * 0.8 + pos.y * 7) * 5;

  return (
    <div
      style={{
        position: "absolute",
        left: `calc(${pos.x * 100}% - ${size / 2}px)`,
        top: `calc(${pos.y * 100}% - ${size / 2}px)`,
        width: size,
        height: size,
        transform: `translate(${sway}px, ${bounce}px) scale(${pulse})`,
        filter: `drop-shadow(0 0 40px ${palette.accent}88)`,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          background: `radial-gradient(circle at 30% 28%, #ffffffaa 0%, ${palette.base} 24%, ${palette.accent} 100%)`,
          boxShadow: `0 0 70px ${palette.accent}66`,
          overflow: "hidden",
        }}
      >
        {layer.name === "saturn" ? (
          <div
            style={{
              position: "absolute",
              left: -size * 0.15,
              top: size * 0.38,
              width: size * 1.3,
              height: size * 0.22,
              borderRadius: "50%",
              border: "8px solid rgba(255,229,184,0.72)",
              transform: "rotate(-12deg)",
            }}
          />
        ) : null}
        <div
          style={{
            position: "absolute",
            left: size * 0.22,
            top: size * 0.3,
            width: size * 0.18,
            height: blink ? size * 0.03 : size * 0.22,
            borderRadius: "50%",
            background: "white",
            border: "4px solid #151515",
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
                transform: `translate(calc(-50% + ${pupilShift}px), -50%)`,
                borderRadius: "50%",
                background: "#111",
              }}
            />
          ) : null}
        </div>
        <div
          style={{
            position: "absolute",
            right: size * 0.22,
            top: size * 0.3,
            width: size * 0.18,
            height: blink ? size * 0.03 : size * 0.22,
            borderRadius: "50%",
            background: "white",
            border: "4px solid #151515",
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
                transform: `translate(calc(-50% + ${pupilShift}px), -50%)`,
                borderRadius: "50%",
                background: "#111",
              }}
            />
          ) : null}
        </div>
        <div
          style={{
            position: "absolute",
            left: "50%",
            bottom: size * 0.18,
            width: size * 0.28,
            height: size * 0.12,
            transform: "translateX(-50%)",
            borderBottom: "6px solid #1c1420",
            borderRadius: "0 0 999px 999px",
          }}
        />
      </div>
    </div>
  );
};

const SceneText: React.FC<{scene: AstroScene | undefined; progress: number}> = ({scene, progress}) => {
  const content = scene?.text?.content ?? "";
  const lines = splitText(content);
  const enter = spring({fps: 30, frame: Math.floor(progress * 30), config: {damping: 200}});
  const scale = interpolate(enter, [0, 1], [0.88, 1]);

  return (
    <div
      style={{
        position: "absolute",
        top: 120,
        left: 60,
        right: 60,
        transform: `scale(${scale})`,
      }}
    >
      {lines.map((line, i) => (
        <div
          key={i}
          style={{
            display: "inline-block",
            marginBottom: 18,
            padding: "10px 18px",
            borderRadius: 999,
            background: "rgba(4, 8, 18, 0.72)",
            fontFamily: "Montserrat, DejaVu Sans, sans-serif",
            fontWeight: 800,
            fontSize: line.length > 18 ? 54 : 64,
            lineHeight: 1.04,
            color: accentPalette.text,
            boxShadow: "0 8px 30px rgba(0,0,0,0.28)",
          }}
        >
          {line.split(" ").map((word, idx) => {
            const isNumber = /\d/.test(word);
            const isPlanet = ["earth", "sun", "jupiter", "saturn", "mars"].includes(word.toLowerCase().replace(/[^\w]/g, ""));
            return (
              <span
                key={`${word}-${idx}`}
                style={{
                  color: isNumber ? accentPalette.yellow : isPlanet ? accentPalette.cyan : accentPalette.text,
                  fontSize: isNumber ? "1.18em" : "1em",
                  marginRight: 12,
                  textShadow: isNumber ? "0 0 16px rgba(255,213,74,0.45)" : "0 0 10px rgba(255,255,255,0.18)",
                }}
              >
                {word}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

export const AstroShortComposition: React.FC<{scriptData: AstroScriptData}> = ({scriptData}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const seconds = frame / fps;
  const hookLength = 2.2;
  const scenes = scriptData.timeline ?? [];
  const activeScene = seconds < hookLength ? undefined : getSceneAtTime(scenes, seconds - hookLength);
  const sceneProgress =
    activeScene == null
      ? Math.min(seconds / hookLength, 1)
      : (seconds - hookLength - (activeScene.time_start ?? 0)) / Math.max((activeScene.time_end ?? 4) - (activeScene.time_start ?? 0), 0.01);
  const globalProgress = frame / durationInFrames;
  const hookScale = interpolate(frame, [0, 14], [0.62, 1], {extrapolateRight: "clamp"});

  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(circle at top, #1a265f 0%, #090b17 46%, #04050a 100%)",
        overflow: "hidden",
        fontFamily: "Montserrat, DejaVu Sans, sans-serif",
      }}
    >
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 22% 18%, rgba(146,98,255,0.28), transparent 32%), radial-gradient(circle at 80% 68%, rgba(255,97,190,0.22), transparent 28%), radial-gradient(circle at 55% 42%, rgba(58,151,255,0.18), transparent 34%)",
        }}
      />
      <Starfield />
      {seconds < hookLength ? (
        <div
          style={{
            position: "absolute",
            left: 70,
            right: 70,
            top: 280,
            color: "white",
            fontSize: 96,
            fontWeight: 900,
            lineHeight: 0.95,
            transform: `scale(${hookScale})`,
            textShadow: "0 18px 40px rgba(0,0,0,0.45)",
          }}
        >
          {scriptData.idea?.hook ?? scriptData.idea?.title}
          <div
            style={{
              marginTop: 24,
              width: `${interpolate(frame, [0, 18], [0, 420], {extrapolateRight: "clamp"})}px`,
              height: 8,
              borderRadius: 999,
              background: accentPalette.magenta,
              boxShadow: "0 0 20px rgba(255,105,212,0.7)",
            }}
          />
        </div>
      ) : (
        <>
          {activeScene?.layers
            ?.filter((layer: AstroLayer) => layer.type === "planet")
            .map((layer: AstroLayer, index: number) => (
            <PlanetCharacter key={`${layer.name}-${index}`} layer={layer} time={seconds} />
          ))}
          <SceneText scene={activeScene} progress={sceneProgress} />
        </>
      )}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          height: 10,
          width: `${globalProgress * 100}%`,
          background: "linear-gradient(90deg, #ffcf42, #ff6bd6)",
          boxShadow: "0 0 18px rgba(255,107,214,0.8)",
        }}
      />
    </AbsoluteFill>
  );
};

export const astroShortDuration = (data: AstroScriptData) => getDuration(data, 30);

export const AstroShortRemotionRoot: React.FC<{scriptData: AstroScriptData}> = ({scriptData}) => {
  return <AstroShortComposition scriptData={scriptData} />;
};
