import React, { useState } from "react";
import { Eye, EyeOff, TriangleAlert } from "lucide-react";

interface Props {
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  minLength?: number;
  autoFocus?: boolean;
  placeholder?: string;
  autoComplete?: string;
  id?: string;
  warnCapsLock?: boolean;
}

export default function PasswordInput({ value, onChange, required, minLength, autoFocus, placeholder, autoComplete, id, warnCapsLock = true }: Props) {
  const [visible, setVisible] = useState(false);
  const [capsOn, setCapsOn] = useState(false);

  const checkCaps = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!warnCapsLock) return;
    if (typeof e.getModifierState === "function") {
      setCapsOn(e.getModifierState("CapsLock"));
    }
  };

  return (
    <div>
      <div className="password-input-wrap">
        <input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyUp={checkCaps}
          onKeyDown={checkCaps}
          onBlur={() => setCapsOn(false)}
          required={required}
          minLength={minLength}
          autoFocus={autoFocus}
          placeholder={placeholder}
          autoComplete={autoComplete}
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
          tabIndex={-1}
        >
          {visible ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
      {capsOn && (
        <div className="caps-lock-warning"><TriangleAlert size={13} /> Caps Lock is on</div>
      )}
    </div>
  );
}
