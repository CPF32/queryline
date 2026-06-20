const { app } = require("electron");
const fs = require("node:fs");
const path = require("node:path");

const projectRoot = path.join(__dirname, "..");

function getAppDataDir() {
  return app.isPackaged ? app.getPath("userData") : projectRoot;
}

function readSetupState() {
  const setupPath = path.join(getAppDataDir(), "setup.json");
  if (!fs.existsSync(setupPath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(setupPath, "utf8"));
  } catch {
    return null;
  }
}

function readEnvValue(key, defaultValue = "") {
  const envPath = path.join(getAppDataDir(), ".env");
  if (!fs.existsSync(envPath)) {
    return defaultValue;
  }

  const content = fs.readFileSync(envPath, "utf8");
  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const separator = trimmed.indexOf("=");
    if (separator === -1) {
      continue;
    }

    const name = trimmed.slice(0, separator).trim();
    if (name !== key) {
      continue;
    }

    let value = trimmed.slice(separator + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    return value || defaultValue;
  }

  return defaultValue;
}

function shouldAutoStartOllama() {
  const state = readSetupState();
  if (state?.ollama_self_host === true) {
    return true;
  }
  return readEnvValue("LLM_PROVIDER") === "ollama";
}

function getOllamaBaseUrl() {
  return readEnvValue("OLLAMA_BASE_URL", "http://127.0.0.1:11434").replace(/\/$/, "");
}

module.exports = {
  getAppDataDir,
  readSetupState,
  readEnvValue,
  shouldAutoStartOllama,
  getOllamaBaseUrl,
};
