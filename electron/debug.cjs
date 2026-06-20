const electron = require("electron/main");
console.log("type:", typeof electron);
console.log("app:", electron?.app);
console.log("keys:", Object.keys(electron).slice(0,8));
setTimeout(() => process.exit(0), 500);
