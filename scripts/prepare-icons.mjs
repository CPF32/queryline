import { copyFileSync, existsSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import pngToIco from "png-to-ico";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const buildDir = path.join(root, "build");
const iconPng = path.join(buildDir, "icon.png");
const iconIco = path.join(buildDir, "icon.ico");

function ensurePng(sourcePath) {
  const probe = spawnSync("file", ["-b", sourcePath], { encoding: "utf8" });
  const description = probe.stdout?.trim() ?? "";
  if (description.startsWith("PNG image")) {
    return;
  }

  spawnSync("sips", ["-s", "format", "png", sourcePath, "--out", iconPng], {
    stdio: "inherit",
  });
}

if (!existsSync(iconPng)) {
  console.error("Missing build/icon.png — add a 1024×1024 app icon first.");
  process.exit(1);
}

ensurePng(iconPng);

const icoBuffer = await pngToIco(iconPng);
writeFileSync(iconIco, icoBuffer);
console.log(`Wrote ${iconIco}`);

const publicDir = path.join(root, "public");
const publicIcon = path.join(publicDir, "icon.png");
copyFileSync(iconPng, publicIcon);
console.log(`Wrote ${publicIcon}`);
