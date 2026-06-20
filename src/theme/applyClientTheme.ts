import { clientTheme, type ThemeMode } from "@/theme/clientTheme.config";

const FONT_LINK_ID = "client-theme-fonts";

function setVar(name: string, value: string, target: HTMLElement) {
  target.style.setProperty(name, value);
}

function applyColorTokens(mode: ThemeMode, root: HTMLElement) {
  const tokens = clientTheme.modes[mode];

  setVar("--font", clientTheme.fonts.sans, root);
  setVar("--font-mono", clientTheme.fonts.mono, root);

  setVar("--bg", tokens.bg, root);
  setVar("--bg-subtle", tokens.bgSubtle, root);
  setVar("--surface", tokens.surface, root);
  setVar("--surface-raised", tokens.surfaceRaised, root);
  setVar("--surface-hover", tokens.surfaceHover, root);
  setVar("--surface-overlay", tokens.surfaceOverlay, root);
  setVar("--border", tokens.border, root);
  setVar("--border-subtle", tokens.borderSubtle, root);
  setVar("--border-strong", tokens.borderStrong, root);
  setVar("--text", tokens.text, root);
  setVar("--text-secondary", tokens.textSecondary, root);
  setVar("--text-muted", tokens.textMuted, root);
  setVar("--accent", tokens.accent, root);
  setVar("--accent-hover", tokens.accentHover, root);
  setVar("--accent-subtle", tokens.accentSubtle, root);
  setVar("--accent-muted", tokens.accentMuted, root);
  setVar("--accent-glow", tokens.accentGlow, root);
  setVar("--success", tokens.success, root);
  setVar("--success-bg", tokens.successBg, root);
  setVar("--success-border", tokens.successBorder, root);
  setVar("--success-text", tokens.successText, root);
  setVar("--warning", tokens.warning, root);
  setVar("--warning-bg", tokens.warningBg, root);
  setVar("--warning-border", tokens.warningBorder, root);
  setVar("--warning-text", tokens.warningText, root);
  setVar("--danger", tokens.danger, root);
  setVar("--danger-bg", tokens.dangerBg, root);
  setVar("--danger-border", tokens.dangerBorder, root);
  setVar("--danger-text", tokens.dangerText, root);
  setVar("--info-text", tokens.infoText, root);
  setVar("--chart-grid", tokens.chartGrid, root);
  setVar("--shadow-sm", tokens.shadowSm, root);
  setVar("--shadow", tokens.shadow, root);
  setVar("--shadow-glow", tokens.shadowGlow, root);
  setVar("--body-background", tokens.bodyBackground, root);

  const layout = clientTheme.layout;
  setVar("--radius-sm", layout.radiusSm, root);
  setVar("--radius", layout.radius, root);
  setVar("--radius-md", layout.radiusMd, root);
  setVar("--radius-lg", layout.radiusLg, root);
  setVar("--radius-xl", layout.radiusXl, root);
  setVar("--sidebar-width", layout.sidebarWidth, root);
  setVar("--chat-sidebar-width", layout.chatSidebarWidth, root);
  setVar("--nav-height", layout.navHeight, root);
  setVar("--content-max", layout.contentMax, root);
  setVar("--transition-fast", layout.transitionFast, root);
  setVar("--transition-base", layout.transitionBase, root);

  setVar("--icon-stroke", String(clientTheme.icons.strokeWidth), root);
}

export function injectClientFonts() {
  if (document.getElementById(FONT_LINK_ID)) {
    return;
  }

  const link = document.createElement("link");
  link.id = FONT_LINK_ID;
  link.rel = "stylesheet";
  link.href = clientTheme.fonts.googleFontsUrl;
  document.head.appendChild(link);
}

export function applyClientTheme(mode: ThemeMode) {
  const root = document.documentElement;
  root.dataset.theme = mode;
  applyColorTokens(mode, root);
  document.title = clientTheme.brand.documentTitle;
}

export function getChartColors(): string[] {
  return [...clientTheme.charts.colors];
}
