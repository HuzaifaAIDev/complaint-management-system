import React, { useState } from "react";
import { User, KeyRound, Monitor, Sun, Moon, ShieldCheck, UserCog2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useToast } from "../context/ToastContext";
import * as authService from "../services/authService";
import { ApiError } from "../services/apiClient";
import PasswordStrength, { isPasswordValid } from "../components/PasswordStrength";
import { formatPkDateTime } from "../utils/datetime";
import PasswordInput from "../components/PasswordInput";

export default function ProfilePage() {
  const { user, refresh } = useAuth();
  const { preference, setPreference } = useTheme();
  const toast = useToast();

  const [name, setName] = useState(user?.name || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [location, setLocation] = useState(user?.location || "");
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileFieldErrors, setProfileFieldErrors] = useState<Record<string, string>>({});

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  if (!user) return null;

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileFieldErrors({});
    setSavingProfile(true);
    try {
      await authService.updateProfile({ name, phone: user.role === "customer" ? phone : undefined, location: user.role === "customer" ? location : undefined });
      await refresh();
      toast.success("Profile updated successfully.");
    } catch (err) {
      if (err instanceof ApiError && err.fields) setProfileFieldErrors(err.fields);
      toast.error(err instanceof ApiError ? err.message : "Unable to update profile.");
    } finally {
      setSavingProfile(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);
    if (!isPasswordValid(newPassword)) {
      setPasswordError("Your new password doesn't meet all the requirements below.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Passwords do not match.");
      return;
    }
    setChangingPassword(true);
    try {
      await authService.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      toast.success("Password changed successfully.");
    } catch (err) {
      setPasswordError(err instanceof ApiError ? err.message : "Unable to change password.");
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="page page-narrow">
      {/* <span className="eyebrow">Account</span> */}
      <h1><span className="page-header-icon"><UserCog2 size={17} /></span> Profile Setting</h1>

      <div className="detail-card" style={{ marginBottom: 18 }}>
        <h2><User size={16} /> Profile</h2>
        <form onSubmit={handleProfileSave}>
          <label>Full name<input value={name} onChange={(e) => setName(e.target.value)} required /></label>
          <label>Email<input value={user.email} disabled /></label>
          <label>Role<input value={user.role} disabled style={{ textTransform: "capitalize" }} /></label>
          {user.role === "customer" && (
            <>
              <label>
                Phone number
                <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="03001234567" inputMode="numeric" maxLength={11} />
                {profileFieldErrors.phone && <span className="field-error">{profileFieldErrors.phone}</span>}
              </label>
              <label>
                Location
                <input value={location} onChange={(e) => setLocation(e.target.value)} placeholder="City, Area, Street" />
                {profileFieldErrors.location && <span className="field-error">{profileFieldErrors.location}</span>}
              </label>
            </>
          )}
          <button type="submit" className="btn-primary" disabled={savingProfile}>
            {savingProfile ? "Saving..." : "Save changes"}
          </button>
        </form>
      </div>

      <div className="detail-card" style={{ marginBottom: 18 }}>
        <h2><KeyRound size={16} /> Change password</h2>
        {user.auth_provider === "google" ? (
          <p className="muted">
            This account signs in with Google. There's no password to change here — manage your
            account security directly through your Google account.
          </p>
        ) : (
          <form onSubmit={handlePasswordChange}>
            {passwordError && <div className="alert alert-error">{passwordError}</div>}
            <label>
              Current password
              <PasswordInput value={currentPassword} onChange={setCurrentPassword} required autoComplete="current-password" />
            </label>
            <label>
              New password
              <PasswordInput value={newPassword} onChange={setNewPassword} required minLength={8} autoComplete="new-password" />
              <PasswordStrength value={newPassword} />
            </label>
            <label>
              Confirm new password
              <PasswordInput value={confirmPassword} onChange={setConfirmPassword} required autoComplete="new-password" />
              {confirmPassword && confirmPassword !== newPassword && (
                <span className="field-error">Passwords do not match</span>
              )}
            </label>
            <button type="submit" className="btn-primary" disabled={changingPassword}>
              {changingPassword ? "Updating..." : "Change password"}
            </button>
          </form>
        )}
      </div>

      <div className="detail-card" style={{ marginBottom: 18 }}>
        <h2><ShieldCheck size={16} /> Security</h2>
        <dl className="meta-list">
          <dt>Last login</dt>
          <dd>{formatPkDateTime(user.last_login_at)}</dd>
          <dt>Password last changed</dt>
          <dd>{formatPkDateTime(user.password_changed_at)}</dd>
        </dl>
      </div>

      <div className="detail-card">
        <h2>Appearance</h2>
        <div className="theme-toggle-row">
          <ThemeOption active={preference === "light"} icon={<Sun size={15} />} label="Light" onClick={() => setPreference("light")} />
          <ThemeOption active={preference === "dark"} icon={<Moon size={15} />} label="Dark" onClick={() => setPreference("dark")} />
          <ThemeOption active={preference === "system"} icon={<Monitor size={15} />} label="System" onClick={() => setPreference("system")} />
        </div>
        <p className="hint" style={{ marginTop: 10 }}>Only your theme preference is stored on this device — no other data is saved locally.</p>
      </div>
    </div>
  );
}

function ThemeOption({ active, icon, label, onClick }: { active: boolean; icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button type="button" className={`theme-option${active ? " theme-option-active" : ""}`} onClick={onClick} aria-pressed={active}>
      {icon} {label}
    </button>
  );
}
