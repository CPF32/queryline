const { app, BrowserWindow } = require("electron");
const { autoUpdater } = require("electron-updater");

/** @type {import("electron").BrowserWindow | null} */
let targetWindow = null;

autoUpdater.autoDownload = false;
autoUpdater.autoInstallOnAppQuit = true;

function send(channel, payload) {
  if (targetWindow && !targetWindow.isDestroyed()) {
    targetWindow.webContents.send(channel, payload);
  }
}

function initAutoUpdater(mainWindow) {
  targetWindow = mainWindow;

  if (!app.isPackaged) {
    return;
  }

  autoUpdater.on("checking-for-update", () => {
    send("app-update-status", { phase: "checking" });
  });

  autoUpdater.on("update-available", (info) => {
    send("app-update-status", {
      phase: "available",
      version: info.version,
      releaseNotes: info.releaseNotes ?? null,
    });
  });

  autoUpdater.on("update-not-available", () => {
    send("app-update-status", { phase: "idle" });
  });

  autoUpdater.on("error", (error) => {
    send("app-update-status", {
      phase: "error",
      message: error.message,
    });
  });

  autoUpdater.on("download-progress", (progress) => {
    send("app-update-status", {
      phase: "downloading",
      percent: progress.percent,
      transferred: progress.transferred,
      total: progress.total,
    });
  });

  autoUpdater.on("update-downloaded", (info) => {
    send("app-update-status", {
      phase: "ready",
      version: info.version,
    });
  });

  setTimeout(() => {
    autoUpdater.checkForUpdates().catch((error) => {
      console.warn("[updater]", error.message);
    });
  }, 3_000);
}

function registerUpdaterIpc(ipcMain) {
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

  ipcMain.handle("get-app-version", () => app.getVersion());
}

module.exports = {
  initAutoUpdater,
  registerUpdaterIpc,
};
