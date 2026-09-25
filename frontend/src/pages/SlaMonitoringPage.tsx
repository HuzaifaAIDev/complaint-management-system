import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { TriangleAlert, TimerReset, CircleCheck, Gauge } from "lucide-react";
import { SlaMonitoringResponse, SlaRequestSummary } from "../types";
import { getSlaMonitoring } from "../services/resourceService";
import { LoadingState, ErrorState, EmptyState, PriorityBadge, formatSlaRemaining } from "../components/Common";

export default function SlaMonitoringPage() {
  const [data, setData] = useState<SlaMonitoringResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSlaMonitoring().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="page"><ErrorState message={error} /></div>;
  if (!data) return <div className="page"><LoadingState /></div>;

  return (
    <div className="page">
      {/* <span className="eyebrow">Operations</span> */}
      <div className="page-header">
        <h1><span className="page-header-icon"><Gauge size={17} /></span> SLA Monitoring Center</h1>
        <div className="kpi-card" style={{ padding: "10px 18px", borderLeftColor: "var(--signal)" }}>
          <div className="kpi-value" style={{ fontSize: "1.3rem" }}>{data.compliance_pct != null ? `${data.compliance_pct}%` : "—"}</div>
          <div className="kpi-label">SLA compliance</div>
        </div>
      </div>

      <SlaSection title="SLA Breached" icon={<TriangleAlert size={16} />} tone="breach" items={data.breached} />
      <SlaSection title="SLA At Risk" icon={<TimerReset size={16} />} tone="warning" items={data.at_risk} />
      <SlaSection title="Within SLA" icon={<CircleCheck size={16} />} tone="success" items={data.within_sla} />
    </div>
  );
}

function SlaSection({ title, icon, tone, items }: { title: string; icon: React.ReactNode; tone: "breach" | "warning" | "success"; items: SlaRequestSummary[] }) {
  return (
    <div className={`detail-card sla-section sla-section-${tone}`} style={{ marginBottom: 18 }}>
      <h2>{icon} {title} <span className="sla-count">{items.length}</span></h2>
      {items.length === 0 && <EmptyState message="Nothing in this bucket right now." />}
      {items.length > 0 && (
        <ul className="sla-list">
          {items.map((r) => (
            <li key={r.id}>
              <Link to={`/requests/${r.id}`} className="sla-ref">{r.reference_number}</Link>
              <span className="sla-category">{r.category_name}</span>
              <PriorityBadge priority={r.priority} />
              <span className={`sla-remaining sla-remaining-${tone}`}>{formatSlaRemaining(r.remaining_seconds)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
