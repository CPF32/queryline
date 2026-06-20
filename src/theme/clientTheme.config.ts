/**
 * Client theme configuration — edit this file to white-label the app.
 *
 * All visual identity (colors, typography, brand, chart palette, layout)
 * flows from this single source. Swap values per client deployment.
 */

export type ThemeMode = "dark" | "light";

export interface ThemeColorTokens {
  bg: string;
  bgSubtle: string;
  surface: string;
  surfaceRaised: string;
  surfaceHover: string;
  surfaceOverlay: string;
  border: string;
  borderSubtle: string;
  borderStrong: string;
  text: string;
  textSecondary: string;
  textMuted: string;
  accent: string;
  accentHover: string;
  accentSubtle: string;
  accentMuted: string;
  accentGlow: string;
  success: string;
  successBg: string;
  successBorder: string;
  successText: string;
  warning: string;
  warningBg: string;
  warningBorder: string;
  warningText: string;
  danger: string;
  dangerBg: string;
  dangerBorder: string;
  dangerText: string;
  infoText: string;
  chartGrid: string;
  shadowSm: string;
  shadow: string;
  shadowGlow: string;
  /** CSS background-image value for the page body */
  bodyBackground: string;
}

export interface ClientThemeConfig {
  brand: {
    /** Primary product name shown in the header */
    name: string;
    /** Short descriptor under the name */
    tagline: string;
    /** Browser tab title */
    documentTitle: string;
  };
  fonts: {
    sans: string;
    mono: string;
    /** Google Fonts stylesheet URL — injected at startup */
    googleFontsUrl: string;
  };
  icons: {
    strokeWidth: number;
    defaultSize: number;
  };
  layout: {
    radiusSm: string;
    radius: string;
    radiusMd: string;
    radiusLg: string;
    radiusXl: string;
    sidebarWidth: string;
    chatSidebarWidth: string;
    navHeight: string;
    contentMax: string;
    transitionFast: string;
    transitionBase: string;
  };
  charts: {
    colors: string[];
  };
  modes: Record<ThemeMode, ThemeColorTokens>;
}

export const clientTheme: ClientThemeConfig = {
  brand: {
    name: "Queryline",
    tagline: "Natural Language SQL",
    documentTitle: "Queryline",
  },

  fonts: {
    sans: '"Plus Jakarta Sans", ui-sans-serif, system-ui, -apple-system, sans-serif',
    mono: '"JetBrains Mono", ui-monospace, Menlo, Monaco, monospace',
    googleFontsUrl:
      "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap",
  },

  icons: {
    strokeWidth: 1.75,
    defaultSize: 16,
  },

  layout: {
    radiusSm: "6px",
    radius: "10px",
    radiusMd: "10px",
    radiusLg: "14px",
    radiusXl: "18px",
    sidebarWidth: "240px",
    chatSidebarWidth: "260px",
    navHeight: "56px",
    contentMax: "760px",
    transitionFast: "0.15s ease",
    transitionBase: "0.2s ease",
  },

  charts: {
    colors: [
      "#FF6320",
      "#FFB020",
      "#FF4081",
      "#38BDF8",
      "#FBBF24",
      "#06B6D4",
      "#F97316",
      "#A855F7",
    ],
  },

  modes: {
    dark: {
      bg: "#07080F",
      bgSubtle: "#0C0E18",
      surface: "#12151F",
      surfaceRaised: "#181C28",
      surfaceHover: "#1E2333",
      surfaceOverlay: "rgba(18, 21, 31, 0.9)",
      border: "#252A3D",
      borderSubtle: "#1A1E2E",
      borderStrong: "#343A52",
      text: "#F0F2FA",
      textSecondary: "#9BA3BC",
      textMuted: "#636B85",
      accent: "#FF6320",
      accentHover: "#E8550F",
      accentSubtle: "rgba(255, 99, 32, 0.14)",
      accentMuted: "rgba(255, 99, 32, 0.38)",
      accentGlow: "rgba(255, 99, 32, 0.32)",
      success: "#34D399",
      successBg: "rgba(52, 211, 153, 0.1)",
      successBorder: "rgba(52, 211, 153, 0.24)",
      successText: "#6EE7B7",
      warning: "#FBBF24",
      warningBg: "rgba(251, 191, 36, 0.1)",
      warningBorder: "rgba(251, 191, 36, 0.24)",
      warningText: "#FCD34D",
      danger: "#FB7185",
      dangerBg: "rgba(251, 113, 133, 0.1)",
      dangerBorder: "rgba(251, 113, 133, 0.24)",
      dangerText: "#FDA4AF",
      infoText: "#93C5FD",
      chartGrid: "#252A3D",
      shadowSm: "0 1px 2px rgba(0, 0, 0, 0.45)",
      shadow: "0 10px 40px rgba(0, 0, 0, 0.5)",
      shadowGlow: "0 0 0 1px var(--accent-muted), 0 0 32px var(--accent-glow)",
      bodyBackground: "none",
    },

    light: {
      bg: "#ECEEF5",
      bgSubtle: "#F5F6FA",
      surface: "#FFFFFF",
      surfaceRaised: "#FFFFFF",
      surfaceHover: "#F0F1F7",
      surfaceOverlay: "rgba(255, 255, 255, 0.92)",
      border: "#D8DCE8",
      borderSubtle: "#E8EBF2",
      borderStrong: "#C2C8D8",
      text: "#0F1220",
      textSecondary: "#4A5168",
      textMuted: "#8B93A8",
      accent: "#EA580C",
      accentHover: "#C2410C",
      accentSubtle: "#FFF7ED",
      accentMuted: "#FDBA74",
      accentGlow: "rgba(234, 88, 12, 0.16)",
      success: "#059669",
      successBg: "#ECFDF5",
      successBorder: "#A7F3D0",
      successText: "#065F46",
      warning: "#D97706",
      warningBg: "#FFFBEB",
      warningBorder: "#FDE68A",
      warningText: "#92400E",
      danger: "#E11D48",
      dangerBg: "#FFF1F2",
      dangerBorder: "#FECDD3",
      dangerText: "#9F1239",
      infoText: "#2563EB",
      chartGrid: "#E2E8F0",
      shadowSm: "0 1px 2px rgba(15, 18, 32, 0.05)",
      shadow: "0 6px 24px rgba(15, 18, 32, 0.08)",
      shadowGlow: "0 0 0 3px var(--accent-subtle)",
      bodyBackground:
        "radial-gradient(ellipse 70% 45% at 50% -15%, rgba(234, 88, 12, 0.08), transparent), radial-gradient(ellipse 50% 35% at 100% 100%, rgba(255, 176, 32, 0.05), transparent)",
    },
  },
};
