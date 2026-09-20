import { useTheme } from "./theme";

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button className="btn btn-ghost text-xs" onClick={toggle} aria-label="Toggle color theme" type="button">
      {theme === "dark" ? "Light" : "Dark"}
    </button>
  );
}
