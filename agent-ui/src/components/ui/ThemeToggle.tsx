/**
 * Reusable dark/light theme switcher.
 *
 * Reads the ThemeContext and renders a single icon button; the active theme is
 * applied on `<html data-theme>` by the provider, so this button works anywhere
 * (chat header, auth pages, admin portal).
 */
import { Moon, Sun } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";

interface ThemeToggleProps {
  /** Visual variant: borderless for dense toolbars, bordered for panels. */
  variant?: "plain" | "boxed";
}

export default function ThemeToggle({ variant = "plain" }: ThemeToggleProps) {
  const { isDark, toggleTheme } = useTheme();
  return (
    <button
      type="button"
      className={variant === "boxed" ? "icon-toggle" : "theme-toggle"}
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      aria-pressed={!isDark}
      title={isDark ? "Light theme" : "Dark theme"}
    >
      {isDark ? <Sun size={17} /> : <Moon size={17} />}
    </button>
  );
}
