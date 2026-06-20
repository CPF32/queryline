const os = require("node:os");
const { contextBridge, ipcRenderer } = require("electron");

function resolveSystemUser() {
  const username = process.env.USERNAME || process.env.USER || os.userInfo().username;
  const domain = process.env.USERDOMAIN;
  if (!username) {
    return null;
  }
  return domain ? `${domain}\\${username}` : username;
}

contextBridge.exposeInMainWorld("desktopApp", {
  platform: process.platform,
  systemUser: resolveSystemUser(),
  pickSqliteFile: () => ipcRenderer.invoke("pick-sqlite-file"),
  getSystemSpecs: () => ipcRenderer.invoke("get-system-specs"),
  recommendOllamaModel: (totalRamGb) => ipcRenderer.invoke("recommend-ollama-model", totalRamGb),
  getOllamaStatus: (baseUrl) => ipcRenderer.invoke("get-ollama-status", baseUrl),
  installOllama: () => ipcRenderer.invoke("install-ollama"),
  startOllama: (baseUrl) => ipcRenderer.invoke("start-ollama", baseUrl),
  pullOllamaModel: (model) => ipcRenderer.invoke("pull-ollama-model", model),
  onOllamaProgress: (callback) => {
    const listener = (_event, progress) => callback(progress);
    ipcRenderer.on("ollama-progress", listener);
    return () => ipcRenderer.removeListener("ollama-progress", listener);
  },
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
});
