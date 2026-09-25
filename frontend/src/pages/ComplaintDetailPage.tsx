import React, { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Complaint, Escalation, User } from "../types";
import * as resourceService from "../services/resourceService";
import { LoadingState, ErrorState, StatusBadge } from "../components/Common";
import { formatPkDateTime } from "../utils/datetime";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../services/apiClient";
import { Phone } from "lucide-react";
import Breadcrumbs from "../components/Breadcrumbs";

const NEXT_STATUS: Record<string, string[]> = {
  open: ["in_review", "escalated"],
  in_review: ["escalated", "resolved"],
  escalated: ["in_review", "resolved"],
  resolved: ["closed"],
  closed: [],
  reopened: ["in_review"],
};

export default function ComplaintDetailPage() {
  const { id } = useParams();
  const complaintId = Number(id);
  const { user } = useAuth();

  const [complaint, setComplaint] = useState<Complaint | null>(null);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [supervisors, setSupervisors] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [resolutionText, setResolutionText] = useState("");
  const [busy, setBusy] = useState(false);

  const canManage = user && ["admin", "supervisor"].includes(user.role);
  const canEscalate = user && ["admin", "supervisor", "agent"].includes(user.role);
  // Contact number is visible to the customer who filed it and to every
  // staff role that might need to reach them.
  const canSeeContactNumber = user && (user.role === "customer" || ["admin", "supervisor", "agent"].includes(user.role));

  const load = useCallback(() => {
    resourceService.getComplaint(complaintId)
      .then((res) => {
        setComplaint(res.complaint);
        setEscalations(res.escalations);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load complaint"));
  }, [complaintId]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (canManage) resourceService.listUsers("supervisor").then((res) => setSupervisors(res.items)).catch(() => {});
  }, [canManage]);

  const runAction = async (fn: () => Promise<any>) => {
    setActionError(null);
    setBusy(true);
    try {
      await fn();
      load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  if (error) return <div className="page"><ErrorState message={error} /></div>;
  if (!complaint) return <div className="page"><LoadingState /></div>;

  const nextStatuses = NEXT_STATUS[complaint.status] || [];
  const needsResolution = nextStatuses.includes("resolved");

  return (
    <div className="page">
      <Breadcrumbs items={
        user?.role === "customer"
          ? [{ label: "My Complaints", to: "/complaints" }, { label: complaint.reference_number }]
          : [{ label: "Dashboard", to: "/dashboard" }, { label: "Complaints", to: "/complaints" }, { label: complaint.reference_number }]
      } />
      <div className="page-header">
        <div>
          {/* <span className="eyebrow">Complaint</span> */}
          <h1 style={{ fontFamily: "var(--font-mono)" }}>{complaint.reference_number}</h1>
        </div>
        <StatusBadge status={complaint.status} />
      </div>
      {actionError && <div className="alert alert-error">{actionError}</div>}

      <div className="detail-grid">
        <section className="detail-main">
          <div className="detail-card">
            <h2>Details</h2>
            <p>{complaint.description}</p>
            <dl className="meta-list">
              <dt>Category</dt><dd>{complaint.category.replace(/_/g, " ")}</dd>
              <dt>Severity</dt><dd>{complaint.severity}</dd>
              {canSeeContactNumber && (
                <>
                  <dt><Phone size={13} style={{ verticalAlign: "-2px", marginRight: 4 }} />Contact number</dt>
                  <dd>{complaint.contact_number}</dd>
                </>
              )}
              <dt>Filed</dt><dd>{formatPkDateTime(complaint.created_at)} (PKT)</dd>
              {complaint.requested_resolution && (<><dt>Requested resolution</dt><dd>{complaint.requested_resolution}</dd></>)}
              {complaint.resolution && (<><dt>Recorded resolution</dt><dd>{complaint.resolution}</dd></>)}
            </dl>
          </div>

          {escalations.length > 0 && (
            <div className="detail-card">
              <h2>Escalations</h2>
              <ul className="history-list">
                {escalations.map((e) => (
                  <li key={e.id}>
                    <strong>{e.escalation_type.replace(/_/g, " ")}</strong> — {e.reason}
                    <div className="muted">{formatPkDateTime(e.escalated_at)} {e.resolved_at ? "· resolved" : "· open"}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <aside className="detail-sidebar">
          {canManage && nextStatuses.length > 0 && (
            <div className="detail-card">
              <h2>Update status</h2>
              {needsResolution && (
                <label>
                  Resolution (required)
                  <textarea rows={3} value={resolutionText} onChange={(e) => setResolutionText(e.target.value)} />
                </label>
              )}
              <div className="btn-row">
                {nextStatuses.map((s) => (
                  <button
                    key={s}
                    disabled={busy || (s === "resolved" && !resolutionText.trim())}
                    className="btn-secondary"
                    onClick={() => runAction(() => resourceService.changeComplaintStatus(complaint.id, s, resolutionText || undefined))}
                  >
                    Mark {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {canEscalate && complaint.status !== "closed" && (
            <div className="detail-card">
              <h2>Escalate</h2>
              <EscalationForm supervisors={supervisors} busy={busy}
                onEscalate={(to, reason, type) => runAction(() => resourceService.createEscalation(complaint.id, { escalated_to: to, reason, escalation_type: type }))} />
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function EscalationForm({ supervisors, busy, onEscalate }: {
  supervisors: User[]; busy: boolean; onEscalate: (to: number, reason: string, type: string) => void;
}) {
  const [to, setTo] = useState("");
  const [reason, setReason] = useState("");
  const [type, setType] = useState("supervisor_intervention");

  return (
    <div>
      <label>
        Escalate to
        <select value={to} onChange={(e) => setTo(e.target.value)}>
          <option value="">Select supervisor</option>
          {supervisors.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </label>
      <label>
        Type
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="sla_breach">SLA breach</option>
          <option value="severe_complaint">Severe complaint</option>
          <option value="supervisor_intervention">Supervisor intervention</option>
          <option value="other">Other</option>
        </select>
      </label>
      <label>
        Reason
        <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
      </label>
      <button className="btn-primary" disabled={!to || !reason.trim() || busy} onClick={() => onEscalate(Number(to), reason, type)}>
        Escalate
      </button>
    </div>
  );
}
