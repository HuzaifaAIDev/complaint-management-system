import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, User, Mail, Lock, Phone, MapPin, Radar, Loader2, CheckCircle2 } from "lucide-react";
import * as authService from "../services/authService";
import { ApiError } from "../services/apiClient";
import { AuthBrandPanel } from "./LoginPage";
import PasswordStrength, { isPasswordValid } from "../components/PasswordStrength";
import PasswordInput from "../components/PasswordInput";
import GoogleSignInButton from "../components/GoogleSignInButton";

// Mirrors the backend rule exactly: 11 digits, numeric only, starting
// with 03. Client-side validation gives an immediate error, but the
// server always re-checks this independently - the frontend is never
// the only line of defense.
const PHONE_PATTERN = /^03[0-9]{9}$/;
export const PHONE_ERROR_MESSAGE = "Phone number must be exactly 11 digits and start with 03.";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "", email: "", password: "", confirmPassword: "",
    phone: "", location: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const update = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }));

  const passwordsMatch = form.confirmPassword.length > 0 && form.confirmPassword === form.password;
  const phoneTouched = form.phone.length > 0;
  const phoneValid = PHONE_PATTERN.test(form.phone);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setFieldErrors({});

    if (!isPasswordValid(form.password)) {
      setError("Your password doesn't meet all the requirements below.");
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (!phoneValid) {
      setFieldErrors((f) => ({ ...f, phone: PHONE_ERROR_MESSAGE }));
      return;
    }
    if (!form.location.trim()) {
      setFieldErrors((f) => ({ ...f, location: "Location is required." }));
      return;
    }

    setSubmitting(true);
    try {
      const res = await authService.register({
        name: form.name,
        email: form.email,
        password: form.password,
        phone: form.phone,
        location: form.location,
      });
      navigate(`/verify-email?email=${encodeURIComponent(res.email)}`);
    } catch (err) {
      if (err instanceof ApiError && err.fields) setFieldErrors(err.fields);
      else if (err instanceof ApiError) setError(err.message);
      else setError("Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <AuthBrandPanel />
      <div className="auth-form-side">
        <form className="auth-card auth-card-wide" onSubmit={handleSubmit} noValidate>
          <Link to="/" className="auth-mobile-brand">
            <span className="sidebar-brand-mark"><Radar size={16} color="#fff" /></span>
            <span>Dispatch</span>
          </Link>

          <h1>Create your account</h1>
          <p className="auth-card-sub">Submit complaints, track their progress, and get updates until they're resolved.</p>
          {error && <div className="alert alert-error"><AlertCircle size={16} />{error}</div>}

          <div className="auth-section-label"><User size={13} /> Your details</div>

          <label htmlFor="reg-name">
            Full name
            <span className="input-icon-wrap">
              <User size={15} />
              <input id="reg-name" value={form.name} onChange={update("name")} placeholder="Jordan Ahmed" required autoFocus autoComplete="name" />
            </span>
          </label>

          <label htmlFor="reg-email">
            Email address
            <span className="input-icon-wrap">
              <Mail size={15} />
              <input id="reg-email" type="email" value={form.email} onChange={update("email")} placeholder="you@example.com" required autoComplete="email" />
            </span>
            {fieldErrors.email && <span className="field-error">{fieldErrors.email}</span>}
          </label>

          <div className="auth-section-label"><Lock size={13} /> Secure your account</div>

          <div className="auth-field-row">
            <label htmlFor="reg-password">
              Password
              <PasswordInput id="reg-password" value={form.password} onChange={(v) => setForm((f) => ({ ...f, password: v }))} required minLength={8} autoComplete="new-password" />
              {fieldErrors.password && <span className="field-error">{fieldErrors.password}</span>}
            </label>
            <label htmlFor="reg-confirm-password">
              Confirm password
              <PasswordInput id="reg-confirm-password" value={form.confirmPassword} onChange={(v) => setForm((f) => ({ ...f, confirmPassword: v }))} required autoComplete="new-password" warnCapsLock={false} />
              {form.confirmPassword && !passwordsMatch && (
                <span className="field-error">Passwords do not match</span>
              )}
              {passwordsMatch && (
                <span className="field-success"><CheckCircle2 size={13} /> Passwords match</span>
              )}
            </label>
          </div>
          <PasswordStrength value={form.password} />

          <div className="auth-section-label"><Phone size={13} /> Contact details</div>

          <div className="auth-field-row">
            <label htmlFor="reg-phone">
              Phone number
              <span className="input-icon-wrap">
                <Phone size={15} />
                <input
                  id="reg-phone"
                  value={form.phone}
                  onChange={update("phone")}
                  placeholder="03001234567"
                  inputMode="numeric"
                  maxLength={11}
                  autoComplete="tel"
                  required
                  aria-invalid={phoneTouched && !phoneValid}
                  aria-describedby="reg-phone-hint"
                />
              </span>
              {fieldErrors.phone ? (
                <span className="field-error">{fieldErrors.phone}</span>
              ) : phoneTouched && !phoneValid ? (
                <span className="field-error" id="reg-phone-hint">{PHONE_ERROR_MESSAGE}</span>
              ) : (
                <span className="field-hint" id="reg-phone-hint">11 digits, starting with 03 (e.g. 03001234567)</span>
              )}
            </label>
            <label htmlFor="reg-location">
              Location
              <span className="input-icon-wrap">
                <MapPin size={15} />
                <input id="reg-location" value={form.location} onChange={update("location")} placeholder="City, Area, Street" autoComplete="street-address" required />
              </span>
              {fieldErrors.location && <span className="field-error">{fieldErrors.location}</span>}
            </label>
          </div>

          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? <><Loader2 size={16} className="btn-loading-spin" /> Creating account...</> : "Register"}
          </button>
          <GoogleSignInButton label="Sign up with Google" />
          <p className="auth-alt">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
