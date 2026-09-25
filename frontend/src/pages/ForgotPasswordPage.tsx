import React, { useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, KeyRound, Mail, Loader2, Radar } from "lucide-react";
import * as authService from "../services/authService";
import { ApiError } from "../services/apiClient";
import { AuthBrandPanel } from "./LoginPage";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await authService.forgotPassword(email);
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <AuthBrandPanel />
      <div className="auth-form-side">
        <div className="auth-card">
          <Link to="/" className="auth-mobile-brand">
            <span className="sidebar-brand-mark"><Radar size={16} color="#fff" /></span>
            <span>Dispatch</span>
          </Link>

          {/* <span className="eyebrow">Account recovery</span> */}
          <h1><KeyRound size={22} style={{ verticalAlign: "-3px", marginRight: 6 }} />Forgot your password?</h1>
          <p className="auth-card-sub">
            Enter your account email and, if it's registered, we'll send a temporary password you can log in with.
          </p>

          {submitted ? (
            <div className="alert" style={{ background: "var(--success-soft)", color: "var(--success)" }}>
              If that email is registered, a temporary password has been sent. You'll be asked to set a new password after logging in with it.
            </div>
          ) : (
            <form onSubmit={handleSubmit} noValidate>
              {error && <div className="alert alert-error"><AlertCircle size={16} />{error}</div>}
              <label htmlFor="forgot-email">
                Email address
                <span className="input-icon-wrap">
                  <Mail size={15} />
                  <input id="forgot-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" required autoFocus autoComplete="email" />
                </span>
              </label>
              <button type="submit" className="btn-primary" disabled={submitting}>
                {submitting ? <><Loader2 size={16} className="btn-loading-spin" /> Sending...</> : "Send temporary password"}
              </button>
            </form>
          )}

          <p className="auth-alt">
            <Link to="/login">Back to log in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
