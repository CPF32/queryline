import { getChartColors } from "@/theme/applyClientTheme";

export interface ChartTheme {
  grid: string;
  tick: string;
  tooltipBg: string;
  tooltipBorder: string;
  tooltipText: string;
  colors: string[];
}

export function getChartTheme(): ChartTheme {
  const style = getComputedStyle(document.documentElement);
  return {
    grid: style.getPropertyValue("--chart-grid").trim() || "#252A3D",
    tick: style.getPropertyValue("--text-muted").trim() || "#636B85",
    tooltipBg: style.getPropertyValue("--surface-raised").trim() || "#181C28",
    tooltipBorder: style.getPropertyValue("--border").trim() || "#343A52",
    tooltipText: style.getPropertyValue("--text").trim() || "#F0F2FA",
    colors: getChartColors(),
  };
}

export function chartTooltipStyle(theme: ChartTheme) {
  return {
    backgroundColor: theme.tooltipBg,
    border: `1px solid ${theme.tooltipBorder}`,
    borderRadius: "8px",
    color: theme.tooltipText,
    fontSize: "12px",
    boxShadow: "0 8px 24px rgba(0, 0, 0, 0.35)",
  };
}
