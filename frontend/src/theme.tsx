import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type Theme = "light" | "dark";
const KEY = "lumina_theme";

function apply(theme: Theme) {
  document.documentElement.setAttribute("data-theme", theme);
}

function read(): Theme {
  const stored = localStorage.getItem(KEY);
  if (stored === "light" || stored === "dark") return stored;
  return "dark";
}

const Ctx = createContext<{ theme: Theme; toggle: () => void; setTheme: (t: Theme) => void } | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    if (typeof document === "undefined") return "dark";
    const t = read();
    apply(t);
    return t;
  });

  const value = useMemo(
    () => ({
      theme,
      setTheme: (t: Theme) => {
        localStorage.setItem(KEY, t);
        apply(t);
        setThemeState(t);
      },
      toggle: () => {
        const next: Theme = theme === "dark" ? "light" : "dark";
        localStorage.setItem(KEY, next);
        apply(next);
        setThemeState(next);
      },
    }),
    [theme]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("theme");
  return ctx;
}
