import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FilePlus2 } from "lucide-react";
import { ServiceCategory } from "../types";
import { listCategories } from "../services/resourceService";
import { createRequest } from "../services/requestService";
import { ApiError } from "../services/apiClient";
import { todayPkDateInputValue } from "../utils/datetime";

const PK_CONTACT_RE = /^03[0-9]{9}$/;

export default function NewRequestPage() {
  const navigate = useNavigate();
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const minDate = todayPkDateInputValue();
  const [form, setForm] = useState({ category_id: "", description: "", location: "", priority: "medium", preferred_date: minDate, contact_number: "" });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listCategories(true).then((res) => {
      setCategories(res.items);
      if (res.items.length > 0) setForm((f) => ({ ...f, category_id: String(res.items[0].id) }));
    });
  }, []);

  const handleContactChange = (raw: string) => {
    // Digits only, capped at 11 characters (Pakistani mobile numbers).
    const digits = raw.replace(/\D/g, "").slice(0, 11);
    setForm((f) => ({ ...f, contact_number: digits }));
  };

  const contactValid = PK_CONTACT_RE.test(form.contact_number);
  // The customer can pick today (Pakistan time) or any future date - never
  // a date that has already passed. The date input's `min` attribute
  // already blocks this in the browser's picker; this is the belt-and-
  // braces client-side check before we even hit the server.
  const dateValid = !!form.preferred_date && form.preferred_date >= minDate;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!contactValid) {
      setError("Enter a valid Pakistani contact number (11 digits, starting with 03).");
      return;
    }
    if (!dateValid) {
      setError("Preferred date cannot be in the past. Please choose today or a later date.");
      return;
    }
    setSubmitting(true);
    try {
      const { service_request } = await createRequest({
        category_id: Number(form.category_id),
        description: form.description,
        location: form.location,
        priority: form.priority,
        preferred_date: form.preferred_date,
        contact_number: form.contact_number,
      });
      navigate(`/requests/${service_request.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit request");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page page-narrow">
      <h1><span className="page-header-icon"><FilePlus2 size={17} /></span> Submit a service request</h1>
      <form className="form-card" onSubmit={handleSubmit}>
        {error && <div className="alert alert-error">{error}</div>}
        <label>
          Service category
          <select value={form.category_id} onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))} required>
            {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        <label>
          Description
          <textarea rows={4} value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} required maxLength={5000} />
        </label>
        <label>
          Location
          <input value={form.location} onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))} required placeholder="Where should the service take place?" />
        </label>
        <label>
          Priority
          <select value={form.priority} onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))} required>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </label>
        <label>
          Preferred date
          <input
            type="date"
            value={form.preferred_date}
            min={minDate}
            onChange={(e) => setForm((f) => ({ ...f, preferred_date: e.target.value }))}
            required
            aria-invalid={form.preferred_date.length > 0 && !dateValid}
          />
          {form.preferred_date.length > 0 && !dateValid && (
            <span className="field-hint field-hint-error">Preferred date cannot be in the past (Pakistan time).</span>
          )}
        </label>
        <label>
          Contact number
          <input
            type="tel"
            inputMode="numeric"
            value={form.contact_number}
            onChange={(e) => handleContactChange(e.target.value)}
            required
            placeholder="03XXXXXXXXX"
            maxLength={11}
            aria-invalid={form.contact_number.length > 0 && !contactValid}
          />
          {form.contact_number.length > 0 && !contactValid && (
            <span className="field-hint field-hint-error">Must be 11 digits and start with 03 (e.g. 03001234567)</span>
          )}
        </label>
        <button type="submit" className="btn-primary" disabled={submitting || !contactValid || !dateValid}>
          {submitting ? "Submitting..." : "Submit request"}
        </button>
      </form>
    </div>
  );
}
