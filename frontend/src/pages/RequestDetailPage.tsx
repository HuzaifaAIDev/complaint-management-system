import React, { useEffect, useState, useCallback } from "react";
import { useParams } from "react-router-dom";
import { ServiceRequest, RequestAttachment, StatusHistoryEntry, User, ServiceCategory } from "../types";
import * as requestService from "../services/requestService";
import { listCategories, listAgentsForCategory } from "../services/resourceService";
import { LoadingState, ErrorState, StatusBadge, PriorityBadge, SlaStateBadge, formatSlaRemaining, PRIORITY_LABELS } from "../components/Common";
import { formatPkDateTime, formatPkDate } from "../utils/datetime";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../services/apiClient";
import { Paperclip, History, Send, UserCog, CircleCheck, FileImage, FileText, Download, ChevronDown, ChevronUp, Phone, Layers, Loader2 } from "lucide-react";
import Breadcrumbs from "../components/Breadcrumbs";

const PRIORITIES = ["low", "medium", "high", "urgent"];

const NEXT_STATUS_OPTIONS: Record<string, string[]> = {
  submitted: ["assigned", "closed"],
  assigned: ["scheduled", "in_progress"],
  scheduled: ["in_progress"],
  in_progress: ["pending_customer", "resolved"],
  pending_customer: ["in_progress", "resolved"],
  resolved: [],
  closed: [],
  reopened: ["assigned", "in_progress"],
};

export default function RequestDetailPage() {
  const { id } = useParams();
  const requestId = Number(id);
  const { user } = useAuth();

  const [sr, setSr] = useState<ServiceRequest | null>(null);
  const [attachments, setAttachments] = useState<RequestAttachment[]>([]);
  const [history, setHistory] = useState<StatusHistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canManage = user && ["admin", "supervisor", "agent"].includes(user.role);
  const isOwner = user?.role === "customer";
  // Agents and supervisors can only view/download attachments - they are
  // never able to upload or attach files. Customers (the request owner)
  // and admins retain full upload access.
  const canUploadAttachments = user && (user.role === "customer" || user.role === "admin");
  // Contact number is only meaningful to staff handling the request (and
  // the customer who provided it); it's always shown to agent/supervisor/admin.
  const canSeeContactNumber = user && (user.role === "customer" || canManage);

  const load = useCallback(() => {
    requestService.getRequest(requestId)
      .then((res) => {
        setSr(res.service_request);
        setAttachments(res.attachments);
        setHistory(res.status_history);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load request"));
  }, [requestId]);

  useEffect(() => { load(); }, [load]);

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
  if (!sr) return <div className="page"><LoadingState /></div>;

  const nextStatuses = NEXT_STATUS_OPTIONS[sr.status] || [];

  return (
    <div className="page">
      <Breadcrumbs items={
        user?.role === "customer"
          ? [{ label: "My Requests", to: "/requests" }, { label: sr.reference_number }]
          : [{ label: "Dashboard", to: "/dashboard" }, { label: "Requests", to: "/requests" }, { label: sr.reference_number }]
      } />
      <div className="page-header">
        <div>
          {/* <span className="eyebrow">Service request</span> */}
          <h1 style={{ fontFamily: "var(--font-mono)" }}>{sr.reference_number}</h1>
        </div>
        <StatusBadge status={sr.status} />
      </div>
      {actionError && <div className="alert alert-error">{actionError}</div>}

      <div className="detail-grid">
        <section className="detail-main">
          <div className="detail-card">
            <h2>Description</h2>
            <p>{sr.description}</p>
            <dl className="meta-list">
              <dt>Category</dt><dd>{sr.category_name || "—"}</dd>
              <dt>Location</dt><dd>{sr.location || "—"}</dd>
              <dt>Priority</dt><dd><PriorityBadge priority={sr.priority} /></dd>
              <dt>Preferred date</dt><dd>{formatPkDate(sr.preferred_date)}</dd>
              {canSeeContactNumber && (
                <>
                  <dt><Phone size={13} style={{ verticalAlign: "-2px", marginRight: 4 }} />Contact number</dt>
                  <dd>{sr.contact_number}</dd>
                </>
              )}
              <dt>Assigned To</dt><dd>{sr.assigned_agent_name || "Not yet assigned"}</dd>
              <dt>Submitted</dt><dd>{formatPkDateTime(sr.created_at)} (PKT)</dd>
              <dt>Assigned At</dt><dd>{sr.assigned_at ? `${formatPkDateTime(sr.assigned_at)} (PKT)` : "—"}</dd>
              <dt>Due At</dt><dd>{sr.sla_resolution_deadline ? `${formatPkDateTime(sr.sla_resolution_deadline)} (PKT)` : "—"}</dd>
              <dt>SLA status</dt>
              <dd>
                <SlaStateBadge state={sr.sla_state} />
                {sr.sla_state && sr.remaining_seconds != null && (
                  <span className="muted" style={{ marginLeft: 8 }}>{formatSlaRemaining(sr.remaining_seconds)}</span>
                )}
              </dd>
            </dl>
          </div>

          <div className="detail-card">
            <h2><Paperclip size={16} /> Attachments</h2>
            {attachments.length === 0 && <p className="muted">No attachments yet.</p>}
            <ul className="attachment-list">
              {attachments.map((a) => (
                <AttachmentItem key={a.id} attachment={a} requestId={sr.id} />
              ))}
            </ul>
            {canUploadAttachments ? (
              <FileUpload requestId={sr.id} onUploaded={load} />
            ) : (
              canManage && <p className="muted field-hint">View only — agents and supervisors cannot upload or attach files.</p>
            )}
          </div>

          <div className="detail-card">
            <h2><History size={16} /> Status history</h2>
            <ul className="history-list">
              {history.map((h) => (
                <li key={h.id}>
                  <StatusBadge status={h.new_status} /> <span className="muted">{formatPkDateTime(h.changed_at)}</span>
                  {h.note && <div className="history-note">{h.note}</div>}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <aside className="detail-sidebar">
          {canManage && nextStatuses.length > 0 && (
            <div className="detail-card">
              <h2><CircleCheck size={16} /> Update status</h2>
              <div className="btn-row">
                {nextStatuses.map((s) => (
                  <button key={s} disabled={busy} className="btn-secondary" onClick={() => runAction(() => requestService.changeStatus(sr.id, s))}>
                    Mark {s.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </div>
          )}

          {isOwner && sr.status === "resolved" && (
            <div className="detail-card">
              <h2>Confirm resolution</h2>
              <div className="btn-row">
                <button disabled={busy} className="btn-primary" onClick={() => runAction(() => requestService.confirmResolution(sr.id))}>
                  <CircleCheck size={15} /> Confirm &amp; close
                </button>
              </div>
            </div>
          )}

          {(user?.role === "admin" || user?.role === "supervisor") && (
            <div className="detail-card">
              <h2><UserCog size={16} /> {sr.assigned_agent_id ? "Reassign complaint" : "Assign complaint"}</h2>
              <AssignTaskForm
                sr={sr}
                busy={busy}
                onAssign={(categoryId, agentId, priority) =>
                  runAction(() =>
                    sr.assigned_agent_id
                      ? requestService.updateAssignment(sr.id, { category_id: categoryId, agent_id: agentId, priority })
                      : requestService.assignComplaint(sr.id, { category_id: categoryId, agent_id: agentId, priority })
                  )
                }
              />
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function AttachmentItem({ attachment, requestId }: { attachment: RequestAttachment; requestId: number }) {
  const [showPreview, setShowPreview] = useState(false);
  const isImage = (attachment.content_type || "").startsWith("image/");
  const downloadUrl = requestService.attachmentDownloadUrl(requestId, attachment.id);

  const formatSize = (bytes: number | null) => {
    if (!bytes) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <li className="attachment-row">
      <div className="attachment-row-main">
        {isImage ? <FileImage size={16} /> : <FileText size={16} />}
        <div className="attachment-row-info">
          <span className="attachment-name">{attachment.original_filename}</span>
          <span className="muted attachment-meta">
            {formatSize(attachment.size_bytes)} · {formatPkDate(attachment.uploaded_at)}
          </span>
        </div>
        <div className="attachment-actions">
          {isImage && (
            <button className="btn-link" onClick={() => setShowPreview((v) => !v)} aria-expanded={showPreview}>
              {showPreview ? <ChevronUp size={14} /> : <ChevronDown size={14} />} Preview
            </button>
          )}
          <a className="btn-link" href={downloadUrl} target="_blank" rel="noreferrer"><Download size={14} /> Download</a>
        </div>
      </div>
      {isImage && showPreview && (
        <img src={downloadUrl} alt={attachment.original_filename} className="attachment-preview-image" />
      )}
    </li>
  );
}

function FileUpload({ requestId, onUploaded }: { requestId: number; onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      await requestService.uploadAttachment(requestId, file);
      setFile(null);
      onUploaded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-row">
      {error && <div className="field-error">{error}</div>}
      <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <button className="btn-secondary" disabled={!file || uploading} onClick={handleUpload}>
        <Send size={14} /> {uploading ? "Uploading..." : "Upload"}
      </button>
    </div>
  );
}

/**
 * Assignment workflow, in this exact order:
 *   1. Select Category
 *   2. Select Agent  - the dropdown is always filtered to agents who
 *      belong to the selected category; it re-fetches and clears
 *      whenever the category changes, so a mismatched pairing can never
 *      be submitted from here. The backend independently re-validates
 *      this pairing regardless.
 *   3. Select Priority
 *   4/5. The SLA and due date/time are computed by the server and shown
 *      as a live preview once category+priority are chosen - never
 *      calculated client-side.
 */
function AssignTaskForm({
  sr, busy, onAssign,
}: {
  sr: ServiceRequest;
  busy: boolean;
  onAssign: (categoryId: number, agentId: number, priority: string) => void;
}) {
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [categoryId, setCategoryId] = useState<string>(sr.category_id ? String(sr.category_id) : "");
  const [agents, setAgents] = useState<User[]>([]);
  const [agentId, setAgentId] = useState<string>(sr.assigned_agent_id ? String(sr.assigned_agent_id) : "");
  const [priority, setPriority] = useState<string>(sr.priority || "medium");
  const [loadingAgents, setLoadingAgents] = useState(false);

  useEffect(() => {
    listCategories(true).then((res) => setCategories(res.items)).catch(() => {});
  }, []);

  useEffect(() => {
    setAgentId(sr.assigned_agent_id && String(sr.category_id) === categoryId ? String(sr.assigned_agent_id) : "");
    setAgents([]);
    if (!categoryId) return;
    setLoadingAgents(true);
    listAgentsForCategory(Number(categoryId))
      .then((res) => setAgents(res.items))
      .finally(() => setLoadingAgents(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryId]);

  const selectedCategory = categories.find((c) => String(c.id) === categoryId);
  const dueAtPreview = computeDuePreview(selectedCategory, priority);

  return (
    <div className="assign-task-form">
      <label>
        <span className="assign-step-label"><Layers size={12} /> Step 1 &middot; Select Category</span>
        <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
          <option value="">Select category</option>
          {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </label>

      <label>
        <span className="assign-step-label">Step 2 &middot; Select Agent</span>
        <select value={agentId} onChange={(e) => setAgentId(e.target.value)} disabled={!categoryId || loadingAgents}>
          <option value="">
            {loadingAgents ? "Loading agents..." : !categoryId ? "Select a category first" : agents.length === 0 ? "No agents in this category" : "Select agent"}
          </option>
          {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        {categoryId && !loadingAgents && agents.length === 0 && (
          <span className="field-hint">No agents currently belong to this category. Add one from Users &amp; Agents.</span>
        )}
      </label>

      <label>
        <span className="assign-step-label">Step 3 &middot; Select Priority</span>
        <select value={priority} onChange={(e) => setPriority(e.target.value)}>
          {PRIORITIES.map((p) => <option key={p} value={p}>{PRIORITY_LABELS[p]}</option>)}
        </select>
      </label>

      {selectedCategory && (
        <div className="assign-sla-preview">
          <span className="assign-step-label">Step 4 &middot; SLA (calculated automatically)</span>
          <dl className="meta-list">
            <dt>Assigned At</dt><dd>Now (server time)</dd>
            <dt>Due At</dt><dd>{dueAtPreview}</dd>
          </dl>
        </div>
      )}

      <button
        className="btn-primary"
        disabled={!agentId || !categoryId || busy}
        onClick={() => onAssign(Number(categoryId), Number(agentId), priority)}
      >
        {busy ? <Loader2 size={14} className="btn-loading-spin" /> : null} {sr.assigned_agent_id ? "Reassign Complaint" : "Assign Complaint"}
      </button>
    </div>
  );
}

// Client-side estimate only, shown as a preview while the form is being
// filled in - the server always computes and stores the authoritative
// due date/time from its own clock when the assignment is submitted.
function computeDuePreview(category: ServiceCategory | undefined, priority: string): string {
  if (!category) return "—";
  const fallbackHours: Record<string, number> = { low: 72, medium: 48, high: 24, urgent: 8 };
  const hours = fallbackHours[priority] ?? category.default_sla_hours ?? 48;
  const due = new Date(Date.now() + hours * 3600 * 1000);
  return `${due.toLocaleDateString()}, ${due.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} (approx.)`;
}
