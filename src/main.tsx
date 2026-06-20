import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "@/App";
import { applyClientTheme, injectClientFonts } from "@/theme/applyClientTheme";
import { getInitialTheme, ThemeProvider } from "@/theme/ThemeProvider";
import "@/styles/global.css";

injectClientFonts();
applyClientTheme(getInitialTheme());

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
);
