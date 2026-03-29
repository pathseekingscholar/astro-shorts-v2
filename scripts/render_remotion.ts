import fs from "node:fs";
import path from "node:path";
import {bundle} from "@remotion/bundler";
import {renderMedia, selectComposition} from "@remotion/renderer";

const root = process.cwd();
const entry = path.join(root, "remotion", "index.ts");
const scriptsDir = path.join(root, "scripts_output");
const outputDir = path.join(root, "videos_output");

const args = process.argv.slice(2);
const inputPath = args[0]
  ? path.resolve(root, args[0])
  : fs
      .readdirSync(scriptsDir)
      .filter((file) => file.endsWith(".json"))
      .map((file) => path.join(scriptsDir, file))
      .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];

if (!inputPath || !fs.existsSync(inputPath)) {
  throw new Error("No script JSON found to render.");
}

const scriptData = JSON.parse(fs.readFileSync(inputPath, "utf8"));
const serveUrl = await bundle({entryPoint: entry});
const composition = await selectComposition({
  serveUrl,
  id: "AstroShort",
  inputProps: {scriptData},
});

fs.mkdirSync(outputDir, {recursive: true});
const outputLocation = path.join(outputDir, `${path.parse(inputPath).name}_remotion.mp4`);

await renderMedia({
  codec: "h264",
  composition,
  serveUrl,
  outputLocation,
  inputProps: {scriptData},
});

console.log(outputLocation);
