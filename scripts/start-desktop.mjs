import { startDesktopDev } from "./dev.mjs";

startDesktopDev().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
