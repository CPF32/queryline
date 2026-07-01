const { app, BrowserWindow, shell } = require("electron");
const { autoUpdater } = require("electron-updater");

/** @type {import("electron").BrowserWindow | null} */
let targetWindow = null;

/** @type {Record<string, unknown>} */
let lastStatus = { phase: "idle" };

/** @type {"auto" | "manual"} */
let lastCheckSource = "auto";

const GITHUB_OWNER = "CPF32";
const GITHUB_REPO = "queryline";
const RELEASES_URL = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest`;

function normalizeVersion(version) {
  const cleaned = String(version || "").replace(/^v/i, "").trim();
  const match = cleaned.match(/^(\d+)\.(\d+)\.(\d+)/);
  if (!match) {
    return null;
  }
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

function isValidVersion(version) {
  return normalizeVersion(version) !== null;
}

function isNewerVersion(latest, current) {
  const latestParts = normalizeVersion(latest);
  const currentParts = normalizeVersion(current);
  if (!latestParts || !currentParts) {
    return false;
  }
  for (let index = 0; index < 3; index += 1) {
    if (latestParts[index] > currentParts[index]) {
      return true;
    }
    if (latestParts[index] < currentParts[index]) {
      return false;
    }
  }
  return false;
}

autoUpdater.autoDownload = false;
autoUpdater.autoInstallOnAppQuit = true;
autoUpdater.allowPrerelease = false;

function send(channel, payload) {
  lastStatus = payload;
  if (targetWindow && !targetWindow.isDestroyed()) {
    targetWindow.webContents.send(channel, payload);
  }
}

async function checkGitHubRelease() {
  const response = await fetch(
    `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest`,
    {
      headers: {
        Accept: "application/vnd.github+json",
        "User-Agent": "Queryline-Updater",
      },
    },
  );

  if (!response.ok) {
    throw new Error(`GitHub Releases API returned ${response.status}`);
  }

  const payload = await response.json();
  const latestVersion = String(payload.tag_name || "").replace(/^v/, "").trim();
  const currentVersion = app.getVersion();

  if (!latestVersion || !isValidVersion(latestVersion)) {
    throw new Error("Could not read the latest release version from GitHub.");
  }

  const currentComparable = normalizeVersion(currentVersion);
  const updateAvailable = Boolean(
    currentComparable && isNewerVersion(latestVersion, currentComparable),
  );

  return {
    currentVersion,
    latestVersion,
    releaseNotes: typeof payload.body === "string" ? payload.body : null,
    releaseUrl: typeof payload.html_url === "string" ? payload.html_url : RELEASES_URL,
    updateAvailable,
  };
}

async function applyGitHubFallback(source, primaryError) {
  try {
    const github = await checkGitHubRelease();
    if (github.updateAvailable) {
      send("app-update-status", {
        phase: "available",
        source,
        version: github.latestVersion,
        currentVersion: github.currentVersion,
        releaseNotes: github.releaseNotes,
        manualDownloadUrl: github.releaseUrl,
        fallback: true,
        message:
          `Version ${github.latestVersion} is available on GitHub. ` +
          "Automatic download is unavailable in this build, so use Download from GitHub.",
      });
      return { checking: false, fallback: true, updateAvailable: true };
    }

    send("app-update-status", {
      phase: "up-to-date",
      source,
      currentVersion: github.currentVersion,
      message: `You're on the latest version (${github.currentVersion}).`,
    });
    return { checking: false, upToDate: true };
  } catch (fallbackError) {
    const message = primaryError
      ? `${primaryError}. GitHub fallback also failed: ${fallbackError.message}`
      : fallbackError.message;
    send("app-update-status", {
      phase: "error",
      source,
      message,
      manualDownloadUrl: RELEASES_URL,
    });
    return { checking: false, error: message };
  }
}

function checkForAppUpdates(source = "auto") {
  if (!app.isPackaged) {
    const message =
      "Auto-update only works in the packaged installer build, not dev Electron runs.";
    if (source === "manual") {
      send("app-update-status", {
        phase: "error",
        source: "manual",
        message,
        manualDownloadUrl: RELEASES_URL,
      });
    }
    return Promise.resolve({ checking: false, error: message });
  }

  lastCheckSource = source === "manual" ? "manual" : "auto";
  send("app-update-status", { phase: "checking", source: lastCheckSource });

  return autoUpdater.checkForUpdates().then(
    () => ({ checking: true }),
    (error) => {
      console.warn("[updater] electron-updater failed:", error.message);
      return applyGitHubFallback(lastCheckSource, error.message);
    },
  );
}

function initAutoUpdater(mainWindow) {
  targetWindow = mainWindow;

  if (!app.isPackaged) {
    return;
  }

  autoUpdater.on("checking-for-update", () => {
    send("app-update-status", { phase: "checking", source: lastCheckSource });
  });

  autoUpdater.on("update-available", (info) => {
    send("app-update-status", {
      phase: "available",
      source: lastCheckSource,
      version: info.version,
      currentVersion: app.getVersion(),
      releaseNotes: info.releaseNotes ?? null,
      fallback: false,
    });
  });

  autoUpdater.on("update-not-available", () => {
    send("app-update-status", {
      phase: "up-to-date",
      source: lastCheckSource,
      currentVersion: app.getVersion(),
    });
  });

  autoUpdater.on("error", (error) => {
    console.warn("[updater] autoUpdater error:", error.message);
    void applyGitHubFallback(lastCheckSource, error.message);
  });

  autoUpdater.on("download-progress", (progress) => {
    send("app-update-status", {
      phase: "downloading",
      percent: progress.percent,
      transferred: progress.transferred,
      total: progress.total,
      version: lastStatus.version,
      fallback: false,
    });
  });

  autoUpdater.on("update-downloaded", (info) => {
    send("app-update-status", {
      phase: "ready",
      version: info.version,
      fallback: false,
    });
  });
}

function registerUpdaterIpc(ipcMain) {
  ipcMain.handle("get-app-version", () => app.getVersion());

  ipcMain.handle("get-app-update-status", () => lastStatus);

  ipcMain.handle("check-app-update", (_event, manual = false) =>
    checkForAppUpdates(manual ? "manual" : "auto"),
  );

  ipcMain.handle("open-release-page", (_event, url = RELEASES_URL) => {
    void shell.openExternal(url || RELEASES_URL);
    return { opened: true };
  });

  ipcMain.handle("download-app-update", async () => {
    if (!app.isPackaged) {
      return { started: false };
    }
    if (lastStatus.fallback || lastStatus.phase === "error" || lastStatus.manualDownloadUrl) {
      await shell.openExternal(String(lastStatus.manualDownloadUrl || RELEASES_URL));
      return { started: true, fallback: true };
    }
    await autoUpdater.downloadUpdate();
    return { started: true };
  });

  ipcMain.handle("install-app-update", () => {
    if (!app.isPackaged) {
      return { installed: false };
    }
    if (lastStatus.fallback) {
      return { installed: false };
    }
    autoUpdater.quitAndInstall(false, true);
    return { installed: true };
  });
}

module.exports = {
  initAutoUpdater,
  registerUpdaterIpc,
  checkForAppUpdates,
  RELEASES_URL,
};
