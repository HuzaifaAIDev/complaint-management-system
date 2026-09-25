import React, { createContext, useContext, useEffect, useState, useCallback } from "react";

type ThemePreference = "light" | "dark" | "system";

interface ThemeContextValue {
  preference: ThemePreference;
  resolvedTheme: "light" | "dark";
  setPreference: (p: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);
const STORAGE_KEY = "theme-preference";

function systemPrefersDark(): boolean {
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(() => {
    // Only the theme preference itself is persisted - never anything
    // sensitive - and it's read defensively in case storage is unavailable.
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "light" || stored === "dark" || stored === "system") return stored;
    } catch {
      /* localStorage may be unavailable (private browsing, etc.) - fall back silently */
    }
    return "system";
  });

  const resolvedTheme: "light" | "dark" = preference === "system" ? (systemPrefersDark() ? "dark" : "light") : preference;

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", resolvedTheme);
  }, [resolvedTheme]);

  useEffect(() => {
    if (preference !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => document.documentElement.setAttribute("data-theme", mq.matches ? "dark" : "light");
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [preference]);

  const setPreference = useCallback((p: ThemePreference) => {
    setPreferenceState(p);
    try {
      window.localStorage.setItem(STORAGE_KEY, p);
    } catch {
      /* ignore storage failures */
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ preference, resolvedTheme, setPreference }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
