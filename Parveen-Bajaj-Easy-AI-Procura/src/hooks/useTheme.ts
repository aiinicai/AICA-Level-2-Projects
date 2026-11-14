import { useEffect, useState } from "react";

export const THEMES = [
  { id: "ink", label: "Ink (dark)" },
  { id: "paper", label: "Paper (light)" },
  { id: "forest", label: "Forest" },
  { id: "ocean", label: "Ocean" },
] as const;
export type ThemeId = (typeof THEMES)[number]["id"];

export function useTheme() {
  const [theme, setTheme] = useState<ThemeId>("ink");
  useEffect(() => {
    const saved = localStorage.getItem("procura-theme") as ThemeId | null;
    if (saved) setTheme(saved);
  }, []);
  useEffect(() => {
    document.documentElement.dataset["theme"] = theme;
    localStorage.setItem("procura-theme", theme);
  }, [theme]);
  return { theme, setTheme };
}
