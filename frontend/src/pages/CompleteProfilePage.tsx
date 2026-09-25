import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Phone, MapPin, Loader2, ShieldCheck, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import * as authService from "../services/authService";
import { ApiError } from "../services/apiClient";
import { PHONE_ERROR_MESSAGE } from "./RegisterPage";

const PHONE_PATTERN = /^03[0-9]{9}$/;

/**
 * Shown once, right after Google Sign-In, to customers who don't yet
 * have a phone number and location on file (Google never supplies
 * either). The rest of the app is inaccessible until this is submitted -
 * see ProfileGate in App.tsx. Never asks for a Residence ID.
 */
export default function CompleteProfilePage() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const [phone, setPhone] = useState("");
  const [location, setLocation] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const phoneTouched = phone.length > 0;
  const phoneValid = PHONE_PATTERN.test(phone);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldErrors({});

    if (!phoneValid) {
      setFieldErrors((f) => ({ ...f, phone: PHONE_ERROR_MESSAGE }));
      return;
    }
    if (!location.trim()) {
      setFieldErrors((f) => ({ ...f, location: "Location is required." }));
      return;
    }

    setSubmitting(true);
    try {
      await authService.updateProfile({ phone, location });
      await refresh();
      toast.success("Profile completed. Welcome!");
      navigate("/requests", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.fields) setFieldErrors(err.fields);
      else toast.error(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-form-side" style={{ margin: "0 auto" }}>
        <form className="auth-card" onSubmit={handleSubmit} noValidate>
          <span className="auth-section-label"><ShieldCheck size={13} /> One last step</span>
          <h1>Complete your profile</h1>
          <p className="auth-card-sub">
            Hi {user?.name || "there"} — we just need your phone number and location before you can submit or track complaints.
          </p>

          <label htmlFor="cp-phone">
            Phone number
            <span className="input-icon-wrap">
              <Phone size={15} />
              <input
                id="cp-phone"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="03001234567"
                inputMode="numeric"
                maxLength={11}
                autoComplete="tel"
                required
                autoFocus
              />
            </span>
            {fieldErrors.phone ? (
              <span className="field-error">{fieldErrors.phone}</span>
            ) : phoneTouched && !phoneValid ? (
              <span className="field-error">{PHONE_ERROR_MESSAGE}</span>
            ) : (
              <span className="field-hint">11 digits, starting with 03 (e.g. 03001234567)</span>
            )}
          </label>

          <label htmlFor="cp-location">
            Location
            <span className="input-icon-wrap">
              <MapPin size={15} />
              <input
                id="cp-location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="City, Area, Street"
                autoComplete="street-address"
                required
              />
            </span>
            {fieldErrors.location && <span className="field-error">{fieldErrors.location}</span>}
          </label>

          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? <><Loader2 size={16} className="btn-loading-spin" /> Saving...</> : "Continue"}
          </button>
        </form>
      </div>
    </div>
  );
}
