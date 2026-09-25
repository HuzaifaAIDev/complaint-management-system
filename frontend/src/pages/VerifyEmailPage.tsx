import React, { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { AlertCircle, CheckCircle2, MailCheck, Loader2, Radar } from "lucide-react";
import * as authService from "../services/authService";
import { ApiError } from "../services/apiClient";
import { AuthBrandPanel } from "./LoginPage";

export default function VerifyEmailPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState(params.get("email") || "");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      await authService.verifyEmail(email, code);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 1200);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verification failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setError(null);
    setInfo(null);
    setResending(true);
    try {
      const res = await authService.resendVerification(email);
      setInfo(res.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not resend code.");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="auth-page">
      <AuthBrandPanel />
      <div className="auth-form-side">
        {success ? (
          <div className="auth-card">
            <Link to="/" className="auth-mobile-brand">
              <span className="sidebar-brand-mark"><Radar size={16} color="#fff" /></span>
              <span>Dispatch</span>
            </Link>
            <div className="alert" style={{ background: "var(--success-soft)", color: "var(--success)" }}>
              <CheckCircle2 size={16} /> Email verified — redirecting you to log in...
            </div>
          </div>
        ) : (
          <form className="auth-card" onSubmit={handleVerify} noValidate>
            <Link to="/" className="auth-mobile-brand">
              <span className="sidebar-brand-mark"><Radar size={16} color="#fff" /></span>
              <span>Dispatch</span>
            </Link>

            <span className="eyebrow">Verify your email</span>
            <h1><MailCheck size={22} style={{ verticalAlign: "-3px", marginRight: 6 }} />Check your inbox</h1>
            <p className="auth-card-sub">
              We sent a verification code to your email. Enter it below to activate your account.
            </p>
            {error && <div className="alert alert-error"><AlertCircle size={16} />{error}</div>}
            {info && <div className="alert" style={{ background: "var(--signal-soft)", color: "var(--signal-ink)" }}>{info}</div>}
            <label htmlFor="verify-email">
              Email address
              <input id="verify-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
            </label>
            <label htmlFor="verify-code">
              Verification code
              <input
                id="verify-code"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                required
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                placeholder="000000"
                autoComplete="one-time-code"
                className="otp-input"
              />
            </label>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? <><Loader2 size={16} className="btn-loading-spin" /> Verifying...</> : "Verify email"}
            </button>
            <button type="button" className="btn-secondary" disabled={resending || !email} onClick={handleResend}>
              {resending ? <><Loader2 size={16} className="btn-loading-spin" /> Sending...</> : "Resend code"}
            </button>
            <p className="auth-alt">
              <Link to="/login">Back to log in</Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
