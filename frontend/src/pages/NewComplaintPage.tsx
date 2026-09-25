import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { MessageSquareWarning } from "lucide-react";
import { createComplaint } from "../services/resourceService";
import { listRequests } from "../services/requestService";
import { ServiceRequest } from "../types";
import { ApiError } from "../services/apiClient";

const CATEGORIES = [
  { value: "delay", label: "Delay" },
  { value: "quality", label: "Quality" },
  { value: "staff_behavior", label: "Staff behavior" },
  { value: "billing", label: "Billing" },
  { value: "incomplete_work", label: "Incomplete work" },
  { value: "other", label: "Other" },
];

const PK_CONTACT_RE = /^03[0-9]{9}$/;

export default function NewComplaintPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [myRequests, setMyRequests] = useState<ServiceRequest[]>([]);
  const [form, setForm] = useState({
    description: "", category: "other", severity: "minor", requested_resolution: "", contact_number: "",
    service_request_id: params.get("request_id") || "",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listRequests({ page_size: 50 }).then((res) => setMyRequests(res.items)).catch(() => {});
  }, []);

  const handleContactChange = (raw: string) => {
    const digits = raw.replace(/\D/g, "").slice(0, 11);
    setForm((f) => ({ ...f, contact_number: digits }));
  };

  const contactValid = PK_CONTACT_RE.test(form.contact_number);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!contactValid) {
      setError("Enter a valid Pakistani contact number (11 digits, starting with 03).");
      return;
    }
    setSubmitting(true);
    try {
      const { complaint } = await createComplaint({
        description: form.description,
        category: form.category,
        severity: form.severity,
        requested_resolution: form.requested_resolution,
        contact_number: form.contact_number,
        service_request_id: form.service_request_id ? Number(form.service_request_id) : undefined,
      });
      navigate(`/complaints/${complaint.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit complaint");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page page-narrow">
      <h1><span className="page-header-icon"><MessageSquareWarning size={17} /></span> Lodge a feedback</h1>
      <form className="form-card" onSubmit={handleSubmit}>
        {error && <div className="alert alert-error">{error}</div>}
        <label>
          Related service request (optional)
          <select value={form.service_request_id} onChange={(e) => setForm((f) => ({ ...f, service_request_id: e.target.value }))}>
            <option value="">Not related to a specific request</option>
            {myRequests.map((r) => <option key={r.id} value={r.id}>{r.reference_number} — {r.description.slice(0, 40)}</option>)}
          </select>
        </label>
        <label>
          Category
          <select value={form.category} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}>
            {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </label>
        <label>
          Severity
          <select value={form.severity} onChange={(e) => setForm((f) => ({ ...f, severity: e.target.value }))}>
            <option value="minor">Minor</option>
            <option value="moderate">Moderate</option>
            <option value="major">Major</option>
            <option value="critical">Critical</option>
          </select>
        </label>
        <label>
          Description
          <textarea rows={4} value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} required maxLength={5000} />
        </label>
        <label>
          Requested resolution
          <textarea rows={3} value={form.requested_resolution} onChange={(e) => setForm((f) => ({ ...f, requested_resolution: e.target.value }))} required maxLength={2000} placeholder="What outcome would resolve this for you?" />
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
        <button type="submit" className="btn-primary" disabled={submitting || !contactValid}>
          {submitting ? "Submitting..." : "Submit feedback"}
        </button>
      </form>
    </div>
  );
}
