const { app } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const projectRoot = path.join(__dirname, "..");

const INHERITED_LLM_ENV_KEYS = [
  "LLM_PROVIDER",
  "ANTHROPIC_API_KEY",
  "ANTHROPIC_MODEL",
  "GEMINI_API_KEY",
  "GEMINI_MODEL",
  "OPENAI_API_KEY",
  "OPENAI_MODEL",
  "OLLAMA_BASE_URL",
  "OLLAMA_MODEL",
];

/** @type {import("node:child_process").ChildProcess | null} */
let backendProcess = null;

function getPythonCommand() {
  if (process.platform === "win32") {
    return path.join(projectRoot, ".venv", "Scripts", "python.exe");
  }
  return path.join(projectRoot, ".venv", "bin", "python");
}

function getBackendCommand() {
  const binaryName =
    process.platform === "win32" ? "text-to-sql-backend.exe" : "text-to-sql-backend";

  if (app.isPackaged) {
    const packagedBinary = path.join(process.resourcesPath, "backend", binaryName);
    if (fs.existsSync(packagedBinary)) {
      return { command: packagedBinary, args: [], cwd: path.dirname(packagedBinary) };
    }
  }

  const python = getPythonCommand();
  return {
    command: python,
    args: [path.join(projectRoot, "desktop", "server.py")],
    cwd: projectRoot,
  };
}

/**
 * @param {(chunk: string) => void} onOutput
 */
function attachProcessLogging(onOutput) {
  if (!backendProcess) {
    return;
  }

  backendProcess.stdout?.on("data", (chunk) => onOutput(chunk.toString()));
  backendProcess.stderr?.on("data", (chunk) => {
    const text = chunk.toString();
    console.error("[backend]", text.trimEnd());
    onOutput(text);
  });
}

function startBackend() {
  return new Promise((resolve, reject) => {
    const { command, args, cwd } = getBackendCommand();

    if (!fs.existsSync(command)) {
      reject(
        new Error(
          app.isPackaged
            ? "Bundled backend binary is missing. Rebuild the desktop app."
            : "Python virtualenv not found. Run: python -m venv .venv && pip install -r requirements.txt",
        ),
      );
      return;
    }

    const env = {
      ...process.env,
      DESKTOP_RUNTIME: "1",
      // Dev desktop shares metadata DB / .env with browser mode (project root).
      // Packaged builds keep an isolated per-user data directory.
      APP_DATA_DIR: app.isPackaged ? app.getPath("userData") : projectRoot,
    };
    for (const key of INHERITED_LLM_ENV_KEYS) {
      delete env[key];
    }

    backendProcess = spawn(command, args, {
      env,
      cwd,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let settled = false;
    const timeout = setTimeout(() => {
      if (!settled) {
        settled = true;
        reject(new Error("Backend failed to start within 60 seconds."));
      }
    }, 60_000);

    const handleOutput = (text) => {
      const match = text.match(/BACKEND_READY:(\d+)/);
      if (match && !settled) {
        settled = true;
        clearTimeout(timeout);
        resolve(Number(match[1]));
      }

      const errorMatch = text.match(/BACKEND_ERROR:(.+)/);
      if (errorMatch && !settled) {
        settled = true;
        clearTimeout(timeout);
        reject(new Error(errorMatch[1].trim()));
      }
    };

    backendProcess.on("error", (error) => {
      if (!settled) {
        settled = true;
        clearTimeout(timeout);
        reject(error);
      }
    });

    backendProcess.on("exit", (code, signal) => {
      if (settled || code === 0) {
        return;
      }
      settled = true;
      clearTimeout(timeout);
      reject(
        new Error(
          signal
            ? `Backend exited unexpectedly (signal ${signal}).`
            : `Backend exited unexpectedly (code ${code ?? "unknown"}).`,
        ),
      );
    });

    attachProcessLogging(handleOutput);
  });
}

function stopBackend() {
  if (!backendProcess || backendProcess.killed) {
    backendProcess = null;
    return;
  }

  backendProcess.kill();
  backendProcess = null;
}

module.exports = { startBackend, stopBackend };
