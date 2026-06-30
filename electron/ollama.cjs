const os = require("node:os");
const { spawn, spawnSync } = require("node:child_process");

const OLLAMA_HEALTH_TIMEOUT_MS = 120_000;
const PULL_TIMEOUT_MS = 30 * 60_000;

/** @type {import("node:child_process").ChildProcess | null} */
let ollamaServeProcess = null;

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

function getSystemSpecs() {
  const totalRamGb = Math.round(os.totalmem() / 1024 ** 3);
  const freeRamGb = Math.round(os.freemem() / 1024 ** 3);
  const cpuCount = os.cpus().length;
  const cpuModel = os.cpus()[0]?.model?.trim() || "Unknown CPU";

  return {
    platform: process.platform,
    arch: os.arch(),
    totalRamGb,
    freeRamGb,
    cpuCount,
    cpuModel,
  };
}

function recommendModel(totalRamGb) {
  if (totalRamGb >= 32) {
    return {
      model: "qwen3-coder:30b",
      label: "Qwen3 Coder 30B",
      reason: "Your system has enough memory for the largest recommended coding model.",
    };
  }
  if (totalRamGb >= 16) {
    return {
      model: "qwen2.5-coder:14b",
      label: "Qwen2.5 Coder 14B",
      reason: "Balanced coding model for systems with 16 GB or more RAM.",
    };
  }
  if (totalRamGb >= 8) {
    return {
      model: "qwen2.5-coder:7b",
      label: "Qwen2.5 Coder 7B",
      reason: "Lightweight coding model suited to 8 GB systems.",
    };
  }
  return {
    model: "llama3.2:3b",
    label: "Llama 3.2 3B",
    reason: "Compact model for systems with limited memory.",
  };
}

async function getOllamaStatus(baseUrl = "http://127.0.0.1:11434") {
  const normalized = baseUrl.replace(/\/$/, "");
  const healthUrl = `${normalized}/api/tags`;
  const running = await isReachable(healthUrl);
  const installed = Boolean(resolveOllamaBinary());
  return { installed, running, baseUrl: normalized };
}

async function waitForOllama(baseUrl, timeoutMs = OLLAMA_HEALTH_TIMEOUT_MS) {
  const healthUrl = `${baseUrl.replace(/\/$/, "")}/api/tags`;
  const started = Date.now();

  while (Date.now() - started < timeoutMs) {
    if (await isReachable(healthUrl)) {
      return;
    }
    await sleep(500);
  }

  throw new Error(`Timed out waiting for Ollama at ${baseUrl}`);
}

function runCommand(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: options.inherit ? "inherit" : "pipe",
      shell: options.shell ?? false,
      env: { ...process.env, ...options.env },
    });

    let stdout = "";
    let stderr = "";

    if (!options.inherit) {
      child.stdout?.on("data", (chunk) => {
        stdout += chunk.toString();
      });
      child.stderr?.on("data", (chunk) => {
        stderr += chunk.toString();
      });
    }

    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
        return;
      }
      reject(new Error(stderr.trim() || stdout.trim() || `${command} exited with code ${code}`));
    });
  });
}

async function installOllama(onProgress) {
  onProgress?.({ phase: "install", message: "Installing Ollama…" });

  if (process.platform === "linux") {
    await runCommand("sh", ["-c", "curl -fsSL https://ollama.com/install.sh | sh"], {
      inherit: true,
      shell: false,
    });
    return { installed: true };
  }

  if (process.platform === "darwin") {
    const brewPath = spawnSync("which", ["brew"], { encoding: "utf8" });
    if (brewPath.status === 0 && brewPath.stdout.trim()) {
      await runCommand("brew", ["install", "ollama"], { inherit: true });
      return { installed: true };
    }

    onProgress?.({
      phase: "install",
      message: "Opening the Ollama download page. Install it, then return here.",
    });
    const { shell } = require("electron");
    await shell.openExternal("https://ollama.com/download/mac");
    throw new Error(
      "Install Ollama from the download page, then click Retry in the setup wizard.",
    );
  }

  if (process.platform === "win32") {
    const winget = spawnSync("where", ["winget"], { encoding: "utf8" });
    if (winget.status === 0) {
      await runCommand(
        "winget",
        ["install", "-e", "--id", "Ollama.Ollama", "--accept-package-agreements", "--accept-source-agreements"],
        { inherit: true, shell: true },
      );
      return { installed: true };
    }

    onProgress?.({
      phase: "install",
      message: "Opening the Ollama download page. Install it, then return here.",
    });
    const { shell } = require("electron");
    await shell.openExternal("https://ollama.com/download/windows");
    throw new Error(
      "Install Ollama from the download page, then click Retry in the setup wizard.",
    );
  }

  throw new Error(`Ollama auto-install is not supported on ${process.platform}.`);
}

async function ensureOllamaRunning(baseUrl = "http://127.0.0.1:11434") {
  const normalized = baseUrl.replace(/\/$/, "");
  const status = await getOllamaStatus(normalized);
  if (status.running) {
    return status;
  }

  let hostname = "";
  try {
    hostname = new URL(normalized).hostname;
  } catch {
    hostname = "";
  }
  const isLocal =
    hostname === "127.0.0.1" || hostname === "localhost" || hostname === "::1";

  if (!isLocal) {
    console.warn(`[ollama] remote server not reachable at ${normalized}`);
    return status;
  }

  if (!status.installed) {
    console.warn("[ollama] not installed, skipping auto-start");
    return status;
  }

  return startOllama(normalized);
}

async function startOllama(baseUrl = "http://127.0.0.1:11434") {
  const status = await getOllamaStatus(baseUrl);
  if (status.running) {
    return status;
  }

  const ollamaBin = resolveOllamaBinary();
  if (!ollamaBin) {
    throw new Error("Ollama is not installed.");
  }

  if (ollamaServeProcess && !ollamaServeProcess.killed) {
    await waitForOllama(baseUrl);
    return getOllamaStatus(baseUrl);
  }

  ollamaServeProcess = spawn(ollamaBin, ["serve"], {
    detached: false,
    stdio: "ignore",
  });

  ollamaServeProcess.on("exit", () => {
    ollamaServeProcess = null;
  });

  await waitForOllama(baseUrl);
  return getOllamaStatus(baseUrl);
}

function pullModel(model, onProgress) {
  const ollamaBin = resolveOllamaBinary();
  if (!ollamaBin) {
    return Promise.reject(new Error("Ollama is not installed."));
  }

  return new Promise((resolve, reject) => {
    const child = spawn(ollamaBin, ["pull", model], {
      stdio: ["ignore", "pipe", "pipe"],
    });

    const handleLine = (line) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return;
      }
      onProgress?.({ phase: "pull", message: trimmed });
    };

    child.stdout.on("data", (chunk) => {
      chunk
        .toString()
        .split(/\r?\n/)
        .forEach(handleLine);
    });

    child.stderr.on("data", (chunk) => {
      chunk
        .toString()
        .split(/\r?\n/)
        .forEach(handleLine);
    });

    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) {
        resolve({ model, complete: true });
        return;
      }
      reject(new Error(`Failed to pull ${model}.`));
    });

    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      reject(new Error(`Timed out pulling ${model}.`));
    }, PULL_TIMEOUT_MS);

    child.on("close", () => clearTimeout(timer));
  });
}

function stopOllamaServe() {
  if (ollamaServeProcess && !ollamaServeProcess.killed) {
    ollamaServeProcess.kill("SIGTERM");
    ollamaServeProcess = null;
  }
}

module.exports = {
  getSystemSpecs,
  recommendModel,
  getOllamaStatus,
  installOllama,
  ensureOllamaRunning,
  startOllama,
  pullModel,
  stopOllamaServe,
  resolveOllamaBinary,
};
