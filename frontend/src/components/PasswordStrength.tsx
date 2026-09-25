import React from "react";
import { Check, X } from "lucide-react";

export const PASSWORD_RULES: { label: string; test: (v: string) => boolean }[] = [
  { label: "At least 8 characters", test: (v) => v.length >= 8 },
  { label: "One uppercase letter", test: (v) => /[A-Z]/.test(v) },
  { label: "One lowercase letter", test: (v) => /[a-z]/.test(v) },
  { label: "One digit", test: (v) => /[0-9]/.test(v) },
  { label: "One special character", test: (v) => /[^A-Za-z0-9]/.test(v) },
];

export function isPasswordValid(value: string): boolean {
  return PASSWORD_RULES.every((r) => r.test(value));
}

function scoreOf(value: string): number {
  return PASSWORD_RULES.filter((r) => r.test(value)).length;
}

const STRENGTH_CONFIG = [
  { max: 1, key: "weak", label: "Weak" },
  { max: 3, key: "fair", label: "Fair" },
  { max: 4, key: "good", label: "Good" },
  { max: 5, key: "strong", label: "Strong" },
];

export default function PasswordStrength({ value }: { value: string }) {
  if (!value) return null;
  const score = scoreOf(value);
  const tier = STRENGTH_CONFIG.find((t) => score <= t.max) || STRENGTH_CONFIG[STRENGTH_CONFIG.length - 1];
  const filled = score === 0 ? 0 : Math.ceil((score / PASSWORD_RULES.length) * 4);

  return (
    <div>
      <div className="password-strength-meter">
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className={`password-strength-seg${i < filled ? ` filled-${tier.key}` : ""}`} />
        ))}
      </div>
      <div className={`password-strength-label label-${tier.key}`}>{tier.label} password</div>
      <ul className="password-rules">
        {PASSWORD_RULES.map((rule) => {
          const ok = rule.test(value);
          return (
            <li key={rule.label} className={ok ? "password-rule-ok" : "password-rule-pending"}>
              {ok ? <Check size={12} /> : <X size={12} />} {rule.label}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
