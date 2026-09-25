import React from "react";
import { Sun, Moon, MonitorSmartphone } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

const ORDER: Array<"light" | "dark" | "system"> = ["light", "dark", "system"];
const ICONS = { light: Sun, dark: Moon, system: MonitorSmartphone };
const LABELS = { light: "Light theme", dark: "Dark theme", system: "System theme" };

/**
 * Compact three-way theme toggle for the topbar. Cycles light -> dark ->
 * system on each click so it stays a single small control rather than a
 * dropdown, while still exposing all three preferences.
 */
export default function ThemeToggle() {
  const { preference, setPreference } = useTheme();
  const Icon = ICONS[preference];

  const handleClick = () => {
    const next = ORDER[(ORDER.indexOf(preference) + 1) % ORDER.length];
    setPreference(next);
  };

  return (
    <button className="theme-toggle" onClick={handleClick} aria-label={`Theme: ${LABELS[preference]}. Click to change.`} title={LABELS[preference]}>
      <Icon size={16} />
    </button>
  );
}
