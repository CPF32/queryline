const { app, BrowserWindow, shell, systemPreferences, dialog, ipcMain } = require("electron");
const path = require("node:path");
const { startBackend, stopBackend } = require("./backend.cjs");
const appData = require("./app-data.cjs");
const ollama = require("./ollama.cjs");
const { initAutoUpdater, registerUpdaterIpc } = require("./updater.cjs");

/** @type {import("electron").BrowserWindow | null} */
let mainWindow = null;

async function ensureSelfHostedOllama() {
  if (!appData.shouldAutoStartOllama()) {
    return;
  }

  try {
    const status = await ollama.ensureOllamaRunning(appData.getOllamaBaseUrl());
    if (status.running) {
      console.log(`[ollama] ready at ${status.baseUrl}`);
    }
  } catch (error) {
    console.warn(
      "[ollama] auto-start failed:",
      error instanceof Error ? error.message : error,
    );
  }
}

async function createWindow() {
  const port = await startBackend();
  const backendUrl = `http://127.0.0.1:${port}`;

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 960,
    minHeight: 640,
    title: "Queryline",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("http://") || url.startsWith("https://")) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });

  mainWindow.webContents.session.setPermissionRequestHandler((_webContents, permission, callback) => {
    if (permission === "media" || permission === "audioCapture") {
      callback(true);
      return;
    }
    callback(false);
  });

  mainWindow.webContents.session.setPermissionCheckHandler((_webContents, permission) => {
    return permission === "media" || permission === "audioCapture";
  });

  initAutoUpdater(mainWindow);
  await mainWindow.loadURL(backendUrl);
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) {
        mainWindow.restore();
      }
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    registerUpdaterIpc(ipcMain);

    ipcMain.handle("pick-sqlite-file", async () => {
      const result = await dialog.showOpenDialog(mainWindow ?? undefined, {
        title: "Select SQLite database",
        properties: ["openFile"],
        filters: [
          { name: "SQLite Database", extensions: ["sqlite", "db", "sqlite3"] },
          { name: "All Files", extensions: ["*"] },
        ],
      });
      if (result.canceled || result.filePaths.length === 0) {
        return null;
      }
      return result.filePaths[0];
    });

    ipcMain.handle("get-system-specs", () => ollama.getSystemSpecs());
    ipcMain.handle("recommend-ollama-model", (_event, totalRamGb) =>
      ollama.recommendModel(totalRamGb),
    );
    ipcMain.handle("get-ollama-status", (_event, baseUrl) => ollama.getOllamaStatus(baseUrl));
    ipcMain.handle("install-ollama", async (event) => {
      const sender = event.sender;
      return ollama.installOllama((progress) => {
        sender.send("ollama-progress", progress);
      });
    });
    ipcMain.handle("start-ollama", (_event, baseUrl) => ollama.startOllama(baseUrl));
    ipcMain.handle("pull-ollama-model", async (event, model) => {
      const sender = event.sender;
      return ollama.pullModel(model, (progress) => {
        sender.send("ollama-progress", progress);
      });
    });

    try {
      if (process.platform === "darwin") {
        await systemPreferences.askForMediaAccess("microphone");
      }

      await ensureSelfHostedOllama();
      await createWindow();
    } catch (error) {
      console.error(error);
      app.quit();
    }
  });

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      try {
        await ensureSelfHostedOllama();
        await createWindow();
      } catch (error) {
        console.error(error);
        app.quit();
      }
    }
  });

  app.on("before-quit", () => {
    ollama.stopOllamaServe();
    stopBackend();
  });

  app.on("window-all-closed", () => {
    ollama.stopOllamaServe();
    stopBackend();
    if (process.platform !== "darwin") {
      app.quit();
    }
  });
}
