const { app, BrowserWindow } = require("electron");
const { autoUpdater } = require("electron-updater");

/** @type {import("electron").BrowserWindow | null} */
let targetWindow = null;

/** @type {Record<string, unknown>} */
let lastStatus = { phase: "idle" };

/** @type {"auto" | "manual"} */
let lastCheckSource = "auto";

autoUpdater.autoDownload = false;
autoUpdater.autoInstallOnAppQuit = true;

function send(channel, payload) {
  lastStatus = payload;
  if (targetWindow && !targetWindow.isDestroyed()) {
    targetWindow.webContents.send(channel, payload);
  }
}

function checkForAppUpdates(source = "auto") {
  if (!app.isPackaged) {
    return Promise.resolve({ checking: false });
  }

  lastCheckSource = source === "manual" ? "manual" : "auto";
  send("app-update-status", { phase: "checking", source: lastCheckSource });
  return autoUpdater.checkForUpdates().then(
    () => ({ checking: true }),
    (error) => {
      console.warn("[updater]", error.message);
      send("app-update-status", {
        phase: "error",
        source: lastCheckSource,
        message: error.message,
      });
      return { checking: false, error: error.message };
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
      releaseNotes: info.releaseNotes ?? null,
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
    send("app-update-status", {
      phase: "error",
      source: lastCheckSource,
      message: error.message,
    });
  });

  autoUpdater.on("download-progress", (progress) => {
    send("app-update-status", {
      phase: "downloading",
      percent: progress.percent,
      transferred: progress.transferred,
      total: progress.total,
      version: lastStatus.version,
    });
  });

  autoUpdater.on("update-downloaded", (info) => {
    send("app-update-status", {
      phase: "ready",
      version: info.version,
    });
  });
}

function registerUpdaterIpc(ipcMain) {
  ipcMain.handle("get-app-version", () => app.getVersion());

  ipcMain.handle("get-app-update-status", () => lastStatus);

  ipcMain.handle("check-app-update", (_event, manual = false) =>
    checkForAppUpdates(manual ? "manual" : "auto"),
  );

  ipcMain.handle("download-app-update", async () => {
    if (!app.isPackaged) {
      return { started: false };
    }
    await autoUpdater.downloadUpdate();
    return { started: true };
  });

  ipcMain.handle("install-app-update", () => {
    if (!app.isPackaged) {
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
};
