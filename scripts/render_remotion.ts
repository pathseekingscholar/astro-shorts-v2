import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import {bundle} from "@remotion/bundler";
import {renderMedia, selectComposition} from "@remotion/renderer";
import {compositionIdForStyle, resolveStyleId} from "../remotion/style-system";
import type {AstroRenderProps, AstroScriptData} from "../remotion/types";

const root = process.cwd();
const entry = path.join(root, "remotion", "index.ts");
const scriptsDir = path.join(root, "scripts_output");
const outputDir = path.join(root, "videos_output");
const publicDir = path.join(root, "public");
const generatedPublicDir = path.join(publicDir, "generated");

function parseArgs(argv: string[]) {
  let inputPath: string | undefined;
  let style: string | undefined;
  let preview = false;

  for (let index = 0; index < argv.length; index++) {
    const token = argv[index];
    if (token === "--preview") {
      preview = true;
      continue;
    }

    if (token === "--style" || token === "-s") {
      style = argv[index + 1];
      index += 1;
      continue;
    }

    if (token.startsWith("--style=")) {
      style = token.slice("--style=".length);
      continue;
    }

    if (!token.startsWith("-") && !inputPath) {
      inputPath = token;
    }
  }

  return {inputPath, style, preview};
}

function findScriptInput(inputPath?: string) {
  if (inputPath) {
    return path.resolve(root, inputPath);
  }

  return fs
    .readdirSync(scriptsDir)
    .filter((file) => file.endsWith(".json"))
    .map((file) => path.join(scriptsDir, file))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
}

function preparePublicAsset(source: string | undefined, prefix: string) {
  if (!source) {
    return undefined;
  }

  if (/^https?:\/\//i.test(source) || /^data:/i.test(source)) {
    return source;
  }

  const absoluteSource = path.isAbsolute(source) ? source : path.resolve(root, source);
  if (!fs.existsSync(absoluteSource)) {
    return undefined;
  }

  const ext = path.extname(absoluteSource) || ".mp4";
  const digest = crypto.createHash("sha1").update(`${prefix}:${absoluteSource}`).digest("hex").slice(0, 10);
  fs.mkdirSync(generatedPublicDir, {recursive: true});
  const targetName = `${prefix}-${digest}${ext}`;
  const targetPath = path.join(generatedPublicDir, targetName);
  fs.copyFileSync(absoluteSource, targetPath);
  return `generated/${targetName}`;
}

function pickBackgroundVideoSrc(scriptData: AstroScriptData, styleId: string) {
  if (styleId !== "character_explainer") {
    return undefined;
  }

  const renderPlan = scriptData.renderPlan ?? scriptData.render_plan;
  const source = renderPlan?.background_video_path ?? renderPlan?.backgroundVideoPath;
  return preparePublicAsset(source, "background-video");
}

function pickBackgroundImageSrc(scriptData: AstroScriptData) {
  const renderPlan = scriptData.renderPlan ?? scriptData.render_plan;
  const source =
    renderPlan?.background_image_path ??
    renderPlan?.backgroundImagePath ??
    (scriptData as AstroScriptData & {background_path?: string}).background_path;
  return preparePublicAsset(source, "background-image");
}

function pickMusicSrc(scriptData: AstroScriptData) {
  const renderPlan = scriptData.renderPlan ?? scriptData.render_plan;
  const source =
    renderPlan?.music_path ??
    renderPlan?.musicPath ??
    (scriptData as AstroScriptData & {music_path?: string}).music_path;
  return preparePublicAsset(source, "music");
}

const args = parseArgs(process.argv.slice(2));
const inputPath = findScriptInput(args.inputPath);

if (!inputPath || !fs.existsSync(inputPath)) {
  throw new Error("No script JSON found to render.");
}

const scriptData = JSON.parse(fs.readFileSync(inputPath, "utf8")) as AstroScriptData;
const resolvedStyle = resolveStyleId(scriptData, args.style);
const backgroundVideoSrc = pickBackgroundVideoSrc(scriptData, resolvedStyle);
const backgroundImageSrc = pickBackgroundImageSrc(scriptData);
const musicSrc = pickMusicSrc(scriptData);
const inputProps: AstroRenderProps = {
  scriptData,
  styleId: resolvedStyle,
  backgroundVideoSrc,
  backgroundImageSrc,
  musicSrc,
};

const serveUrl = await bundle({entryPoint: entry});
const composition = await selectComposition({
  serveUrl,
  id: compositionIdForStyle(resolvedStyle),
  inputProps,
});

fs.mkdirSync(outputDir, {recursive: true});
const outputLocation = path.join(outputDir, `${path.parse(inputPath).name}_${resolvedStyle}_remotion.mp4`);

await renderMedia({
  codec: "h264",
  composition,
  serveUrl,
  outputLocation,
  inputProps,
  scale: args.preview ? 0.5 : 1,
});

console.log(outputLocation);
