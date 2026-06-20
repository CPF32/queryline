import { spawn, spawnSync } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function loadEnvFile() {
  const envPath = path.join(root, ".env");
  if (!existsSync(envPath)) {
    return {};
  }

  const values = {};
  for (const line of readFileSync(envPath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const separator = trimmed.indexOf("=");
    if (separator === -1) {
      continue;
    }

    const key = trimmed.slice(0, separator).trim();
    let value = trimmed.slice(separator + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }

  return values;
}

function resolvePython() {
  const venvPython =
    process.platform === "win32"
      ? path.join(root, ".venv", "Scripts", "python.exe")
      : path.join(root, ".venv", "bin", "python");

  if (existsSync(venvPython)) {
    return venvPython;
  }

  return process.platform === "win32" ? "python" : "python3";
}

function localBin(name) {
  const suffix = process.platform === "win32" ? ".cmd" : "";
  return path.join(root, "node_modules", ".bin", `${name}${suffix}`);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function isReachable(url) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(2_000) });
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForUrl(url, timeoutMs = 90_000) {
  const started = Date.now();

  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(2_000) });
      if (response.ok) {
        return;
      }
    } catch {
      // Keep polling until the service is ready.
    }

    await sleep(500);
  }

  throw new Error(`Timed out waiting for ${url}`);
}

function openUrl(url) {
  const cursorBin = "/Applications/Cursor.app/Contents/Resources/app/bin/cursor";
  if (process.platform === "darwin" && existsSync(cursorBin)) {
    const encoded = encodeURIComponent(url);
    spawn(cursorBin, ["-r", `vscode://vscode.simple-browser/show?url=${encoded}`], {
      detached: true,
      stdio: "ignore",
    }).unref();
    return;
  }

  let command;
  let args;

  if (process.platform === "win32") {
    command = "cmd";
    args = ["/c", "start", "", url];
  } else if (process.platform === "darwin") {
    command = "open";
    args = [url];
  } else {
    command = "xdg-open";
    args = [url];
  }

  spawn(command, args, { detached: true, stdio: "ignore" }).unref();
}

function spawnLogged(label, command, args, env = {}) {
  const childEnv = { ...process.env, ...env };
  delete childEnv.ELECTRON_RUN_AS_NODE;

  console.log(`[${label}] ${command} ${args.join(" ")}`);

  const child = spawn(command, args, {
    cwd: root,
    env: childEnv,
    stdio: "inherit",
  });

  child.on("exit", (code, signal) => {
    if (signal) {
      console.error(`[${label}] stopped (${signal})`);
      return;
    }
    if (code && code !== 0) {
      console.error(`[${label}] exited with code ${code}`);
    }
  });

  return child;
}

function shutdown(children) {
  for (const child of children) {
    if (!child.killed) {
      child.kill("SIGTERM");
    }
  }
}

function resolveOllamaBinary() {
  const lookup = spawnSync(
    process.platform === "win32" ? "where" : "which",
    ["ollama"],
    { encoding: "utf8" },
  );

  if (lookup.status !== 0) {
    return null;
  }

  const line = lookup.stdout.trim().split(/\r?\n/)[0]?.trim();
  return line || null;
}

function isLocalOllamaUrl(url) {
  try {
    const { hostname } = new URL(url);
    return (
      hostname === "127.0.0.1" ||
      hostname === "localhost" ||
      hostname === "::1"
    );
  } catch {
    return false;
  }
}

async function ensureOllamaRunning(ollamaUrl, children) {
  if (!isLocalOllamaUrl(ollamaUrl)) {
    return;
  }

  const healthUrl = `${ollamaUrl}/api/tags`;
  if (await isReachable(healthUrl)) {
    console.log(`[ollama] already running at ${ollamaUrl}`);
    return;
  }

  const ollamaBin = resolveOllamaBinary();
  if (!ollamaBin) {
    console.warn(
      "[ollama] not running and `ollama` CLI not found — install from https://ollama.com",
    );
    return;
  }

  children.push(spawnLogged("ollama", ollamaBin, ["serve"]));
  console.log("Waiting for Ollama…");
  await waitForUrl(healthUrl);
  console.log(`[ollama] ready at ${ollamaUrl}`);
}

export function getDevConfig() {
  const fileEnv = loadEnvFile();
  const backendPort = process.env.PORT || fileEnv.PORT || "5001";
  const backendUrl = `http://127.0.0.1:${backendPort}`;
  const frontendUrl = "http://127.0.0.1:3000";
  const ollamaUrl = (
    process.env.OLLAMA_BASE_URL ||
    fileEnv.OLLAMA_BASE_URL ||
    "http://127.0.0.1:11434"
  ).replace(/\/$/, "");

  return {
    root,
    python: resolvePython(),
    backendPort,
    backendUrl,
    frontendUrl,
    ollamaUrl,
  };
}

export async function startBrowserDev() {
  const { python, backendUrl, frontendUrl, ollamaUrl } = getDevConfig();
  const children = [];

  const onExit = () => {
    shutdown(children);
    process.exit(0);
  };

  process.on("SIGINT", onExit);
  process.on("SIGTERM", onExit);

  await ensureOllamaRunning(ollamaUrl, children);

  if (await isReachable(`${backendUrl}/health`)) {
    console.log(`[backend] already running at ${backendUrl}`);
  } else {
    children.push(
      spawnLogged("backend", python, ["run.py"], {
        PORT: String(getDevConfig().backendPort),
      }),
    );
    console.log("Waiting for backend…");
    await waitForUrl(`${backendUrl}/health`);
  }

  if (await isReachable(frontendUrl)) {
    console.log(`[frontend] already running at ${frontendUrl}`);
  } else {
    children.push(
      spawnLogged(
        "frontend",
        localBin("vite"),
        ["--host", "127.0.0.1", "--port", "3000", "--strictPort"],
        {
          VITE_API_PROXY: backendUrl,
        },
      ),
    );
    console.log("Waiting for frontend…");
    await waitForUrl(frontendUrl);
  }

  console.log(`Opening ${frontendUrl}`);
  openUrl(frontendUrl);

  await new Promise(() => {
    // Keep the launcher alive while child processes run.
  });
}

export async function startDesktopDev() {
  const electronBin = localBin("electron");
  if (!existsSync(electronBin)) {
    throw new Error("Electron is not installed. Run npm install first.");
  }

  const { ollamaUrl } = getDevConfig();
  const ollamaChildren = [];

  await ensureOllamaRunning(ollamaUrl, ollamaChildren);

  console.log("Building frontend…");
  const build = spawnSync(process.platform === "win32" ? "npm.cmd" : "npm", ["run", "build"], {
    cwd: root,
    stdio: "inherit",
    env: process.env,
  });

  if (build.status !== 0) {
    process.exit(build.status ?? 1);
  }

  console.log("Launching desktop app (backend starts automatically)…");

  const childEnv = { ...process.env };
  delete childEnv.ELECTRON_RUN_AS_NODE;

  const desktop = spawn(electronBin, ["."], {
    cwd: root,
    env: childEnv,
    stdio: "inherit",
  });

  desktop.on("exit", (code) => {
    shutdown(ollamaChildren);
    process.exit(code ?? 0);
  });

  process.on("SIGINT", () => {
    shutdown(ollamaChildren);
    if (!desktop.killed) {
      desktop.kill("SIGTERM");
    }
  });
}
