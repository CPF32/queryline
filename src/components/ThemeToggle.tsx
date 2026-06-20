import Icon from "@/components/icons/Icon";
import { useTheme, type Theme } from "@/theme/ThemeProvider";

interface ThemeToggleProps {
  variant?: "button" | "switch";
  value?: Theme;
  onChange?: (theme: Theme) => void;
}

export default function ThemeToggle({
  variant = "button",
  value,
  onChange,
}: ThemeToggleProps) {
  const context = useTheme();
  const theme = value ?? context.theme;
  const isDark = theme === "dark";
  const label = isDark ? "Switch to light mode" : "Switch to dark mode";

  const handleToggle = () => {
    const next = isDark ? "light" : "dark";
    if (onChange) {
      onChange(next);
      return;
    }
    context.toggleTheme();
  };

  if (variant === "switch") {
    return (
      <button
        type="button"
        className={`theme-toggle-switch${isDark ? " theme-toggle-switch--dark" : " theme-toggle-switch--light"}`}
        onClick={handleToggle}
        aria-label={label}
        title={label}
        aria-pressed={isDark}
      >
        <span className="theme-toggle-switch__track">
          <span className="theme-toggle-switch__thumb" aria-hidden />
          <Icon name="moon" size={14} className="theme-toggle-switch__icon theme-toggle-switch__icon--moon" />
          <Icon name="sun" size={14} className="theme-toggle-switch__icon theme-toggle-switch__icon--sun" />
        </span>
      </button>
    );
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={handleToggle}
      aria-label={label}
      title={label}
    >
      <Icon name={isDark ? "sun" : "moon"} size={16} />
    </button>
  );
}
