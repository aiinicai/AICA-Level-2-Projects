import { useEffect } from "react";
import { useWorkspace } from "./store";

/** Applies the workspace theme preference to <html>. */
export function ThemeEffect() {
  const { settings, hydrated } = useWorkspace();

  useEffect(() => {
    if (!hydrated) return;
    const root = document.documentElement;
    const media = window.matchMedia("(prefers-color-scheme: dark)");

    const apply = () => {
      const dark = settings.theme === "dark" || (settings.theme === "system" && media.matches);
      root.classList.toggle("dark", dark);
      document
        .querySelector('meta[name="theme-color"]')
        ?.setAttribute("content", dark ? "#16191f" : "#ffffff");
    };

    apply();
    if (settings.theme === "system") {
      media.addEventListener("change", apply);
      return () => media.removeEventListener("change", apply);
    }
    return undefined;
  }, [settings.theme, hydrated]);

  return null;
}
