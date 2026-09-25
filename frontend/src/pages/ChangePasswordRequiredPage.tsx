import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, ShieldAlert, Loader2, Radar } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import * as authService from "../services/authService";
import { ApiError } from "../services/apiClient";
import PasswordStrength, { isPasswordValid } from "../components/PasswordStrength";
import PasswordInput from "../components/PasswordInput";
import { AuthBrandPanel } from "./LoginPage";
import { getHomePath } from "../utils/roleHome";

export default function ChangePasswordRequiredPage() {
  const { refresh, logout } = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isPasswordValid(newPassword)) {
      setError("Your new password doesn't meet all the requirements below.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await authService.changePassword(currentPassword, newPassword);
      const freshUser = await refresh();
      navigate(freshUser ? getHomePath(freshUser.role) : "/login", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to change password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <AuthBrandPanel />
      <div className="auth-form-side">
        <form className="auth-card" onSubmit={handleSubmit} noValidate>
          <span className="auth-mobile-brand">
            <span className="sidebar-brand-mark"><Radar size={16} color="#fff" /></span>
            <span>Dispatch</span>
          </span>

          {/* <span className="eyebrow">Security</span> */}
          <h1><ShieldAlert size={22} style={{ verticalAlign: "-3px", marginRight: 6 }} />Set a new password</h1>
          <p className="auth-card-sub">
            You're using a temporary password. For your account's security, set a permanent password before continuing.
          </p>
          {error && <div className="alert alert-error"><AlertCircle size={16} />{error}</div>}
          <label htmlFor="cp-current">
            Temporary password
            <PasswordInput id="cp-current" value={currentPassword} onChange={setCurrentPassword} required autoComplete="current-password" warnCapsLock={false} />
          </label>
          <label htmlFor="cp-new">
            New password
            <PasswordInput id="cp-new" value={newPassword} onChange={setNewPassword} required minLength={8} autoComplete="new-password" />
            <PasswordStrength value={newPassword} />
          </label>
          <label htmlFor="cp-confirm">
            Confirm new password
            <PasswordInput id="cp-confirm" value={confirmPassword} onChange={setConfirmPassword} required autoComplete="new-password" warnCapsLock={false} />
            {confirmPassword && confirmPassword !== newPassword && (
              <span className="field-error">Passwords do not match</span>
            )}
          </label>
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? <><Loader2 size={16} className="btn-loading-spin" /> Updating...</> : "Set new password"}
          </button>
          <button type="button" className="btn-secondary" onClick={() => logout().then(() => navigate("/login"))}>
            Log out instead
          </button>
        </form>
      </div>
    </div>
  );
}
