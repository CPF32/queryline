import { startBrowserDev } from "./dev.mjs";

startBrowserDev().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
