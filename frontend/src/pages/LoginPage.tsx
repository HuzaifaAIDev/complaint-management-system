import React, { useState, useEffect } from "react";
import { Link, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import { Radar, AlertCircle, ArrowLeft, Mail, Loader2, ShieldCheck, Gauge, ScrollText } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../services/apiClient";
import PasswordInput from "../components/PasswordInput";
import GoogleSignInButton from "../components/GoogleSignInButton";
import { getHomePath } from "../utils/roleHome";

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
  oauth_failed: "We couldn't complete sign-in with Google. Please try again.",
  oauth_unavailable: "Google Sign-In isn't available right now.",
};

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fromState = (location.state as any)?.from?.pathname;

  useEffect(() => {
    const oauthError = params.get("error");
    if (oauthError) setError(OAUTH_ERROR_MESSAGES[oauthError] || "Sign-in failed. Please try again.");
  }, [params]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login(email, password, remember);
      if (user.must_change_password) {
        navigate("/change-password-required", { replace: true });
      } else {
        navigate(fromState || getHomePath(user.role), { replace: true });
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 403 && err.code === "email_not_verified") {
        navigate(`/verify-email?email=${encodeURIComponent(email)}`);
        return;
      }
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <AuthBrandPanel />
      <div className="auth-form-side">
        <form className="auth-card" onSubmit={handleSubmit} noValidate>
          <Link to="/" className="auth-mobile-brand">
            <span className="sidebar-brand-mark"><Radar size={16} color="#fff" /></span>
            <span>Dispatch</span>
          </Link>

          {/* <span className="eyebrow">Sign in</span> */}
          <h1>Welcome back</h1>
          <p className="auth-card-sub">Log in to track requests, respond to complaints, and stay ahead of SLA deadlines.</p>
          {error && (
            <div className="alert alert-error"><AlertCircle size={16} />{error}</div>
          )}

          <label htmlFor="login-email">
            Email address
            <span className="input-icon-wrap">
              <Mail size={15} />
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoFocus
                autoComplete="email"
              />
            </span>
          </label>

          <label htmlFor="login-password">
            Password
            <PasswordInput id="login-password" value={password} onChange={setPassword} required autoComplete="current-password" />
          </label>

          <div className="auth-checkbox-row">
            <label className="auth-checkbox">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              Remember me for 30 days
            </label>
            <Link to="/forgot-password" className="btn-link">Forgot password?</Link>
          </div>

          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? <><Loader2 size={16} className="btn-loading-spin" /> Logging in...</> : "Log in"}
          </button>
          <GoogleSignInButton label="Continue with Google" />
          <p className="auth-alt">
            Need an account? <Link to="/register">Register as a customer</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

export function AuthBrandPanel() {
  const items: { label: string; color: string; icon: React.ComponentType<any> }[] = [
    { label: "Requests routed and SLA-tracked automatically", color: "var(--signal)", icon: Gauge },
    { label: "Complaints escalated before they go quiet", color: "var(--breach)", icon: ShieldCheck },
    { label: "Every status change kept on the record", color: "var(--success)", icon: ScrollText },
  ];
  return (
    <div className="auth-panel">
      <div className="auth-panel-top">
        <div className="auth-panel-brand-row">
          <Link to="/" className="auth-panel-brand">
            <span className="sidebar-brand-mark"><Radar size={18} color="#fff" /></span>
            <span className="auth-panel-brand-text">Dispatch</span>
          </Link>
          <Link to="/" className="auth-panel-back"><ArrowLeft size={13} /> Back to home</Link>
        </div>
        <h2 className="auth-panel-headline">Run service work like a control room, not an inbox.</h2>
        {/* <p className="auth-panel-sub">
        
          One system for requests, assignments, work orders, complaints and SLA
          monitoring &mdash; with a full audit trail on every record.
        </p> */}
        <p className="auth-panel-sub">
          <strong>
            One system for requests, assignments, work orders, complaints and SLA
            monitoring &mdash; with a full audit trail on every record.
          </strong>
        </p>
        <div className="auth-rail-list">
          {items.map((item) => (
            <div className="auth-rail-item" key={item.label}>
              <span className="auth-rail-icon" style={{ background: `${item.color}22`, color: item.color }}>
                <item.icon size={14} />
              </span>
              {item.label}
            </div>
          ))}
        </div>
        {/* <div className="auth-panel-stats">
          <div className="auth-panel-stat">
            <strong>&lt; 2 min</strong>
            <span>Avg. routing time</span>
          </div>
          <div className="auth-panel-stat">
            <strong>100%</strong>
            <span>Actions audited</span>
          </div>
          <div className="auth-panel-stat">
            <strong>4</strong>
            <span>Role workspaces</span>
          </div>
        </div> */}
      </div>
      <div className="auth-panel-foot">SERVICE &amp; COMPLAINT MANAGEMENT SYSTEM</div>
    </div>
  );
}
