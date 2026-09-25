import React from "react";
import { Loader2, AlertTriangle, Inbox, TriangleAlert } from "lucide-react";

export function LoadingState({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="state-box">
      <Loader2 size={18} className="spin" style={{ marginBottom: 6 }} />
      <div>{label}</div>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="state-box state-error">
      <AlertTriangle size={18} style={{ marginBottom: 6 }} />
      <div>{message}</div>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="state-box">
      <Inbox size={18} style={{ marginBottom: 6, color: "var(--ink-faint)" }} />
      <div>{message}</div>
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  submitted: "#5b6572",
  assigned: "#2f5dff",
  scheduled: "#7c4dff",
  in_progress: "#b3760a",
  pending_customer: "#b3760a",
  resolved: "#12876b",
  closed: "#374151",
  reopened: "#d1461f",
  open: "#5b6572",
  in_review: "#2f5dff",
  escalated: "#d1461f",
};

export function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || "#5b6572";
  return (
    <span className="status-badge" style={{ backgroundColor: `${color}17`, color }}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

const PRIORITY_COLORS: Record<string, string> = {
  low: "#12876b",
  medium: "#2f5dff",
  high: "#b3760a",
  urgent: "#d1461f",
};

// Internally the "urgent" priority value is unchanged (avoids a
// higher-risk database rename), but it's always labeled "Critical" to
// the user, matching Low / Medium / High / Critical everywhere in the UI.
export const PRIORITY_LABELS: Record<string, string> = {
  low: "Low", medium: "Medium", high: "High", urgent: "Critical",
};

export function PriorityBadge({ priority }: { priority: string }) {
  const color = PRIORITY_COLORS[priority] || "#5b6572";
  return (
    <span className="status-badge" style={{ backgroundColor: `${color}17`, color }}>
      {PRIORITY_LABELS[priority] || priority}
    </span>
  );
}

export function BreachTag() {
  return (
    <span className="badge-breach">
      <TriangleAlert size={13} /> Breached
    </span>
  );
}

const SLA_STATE_CONFIG: Record<string, { label: string; color: string }> = {
  breached: { label: "Breached", color: "#d1461f" },
  at_risk: { label: "At risk", color: "#b3760a" },
  within_sla: { label: "On track", color: "#12876b" },
};

/**
 * Renders the three real SLA states the backend computes (breached /
 * at_risk / within_sla). Requests with no active SLA (resolved, closed,
 * or no deadline at all) render nothing rather than a misleading badge -
 * there's no SLA purpose left to communicate once a request is done.
 */
export function SlaStateBadge({ state }: { state?: "within_sla" | "at_risk" | "breached" | null }) {
  if (!state) return <span className="muted">—</span>;
  const config = SLA_STATE_CONFIG[state];
  if (!config) return <span className="muted">—</span>;
  return (
    <span className="status-badge" style={{ backgroundColor: `${config.color}17`, color: config.color }}>
      {config.label}
    </span>
  );
}

export function formatSlaRemaining(seconds: number | null | undefined): string {
  if (seconds == null) return "";
  const abs = Math.abs(Math.round(seconds));
  const h = Math.floor(abs / 3600);
  const m = Math.floor((abs % 3600) / 60);
  const label = h > 0 ? `${h}h ${m}m` : `${m}m`;
  return seconds < 0 ? `Overdue by ${label}` : `Due in ${label}`;
}
