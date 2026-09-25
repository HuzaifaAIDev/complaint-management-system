import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Mail, Phone, MapPin } from "lucide-react";
import { CustomerSummaryResponse } from "../types";
import { getCustomerSummary } from "../services/resourceService";
import { LoadingState, ErrorState, EmptyState, StatusBadge, PriorityBadge } from "../components/Common";
import { formatPkDate } from "../utils/datetime";
import Breadcrumbs from "../components/Breadcrumbs";

export default function CustomerDetailPage() {
  const { id } = useParams();
  const customerId = Number(id);
  const [data, setData] = useState<CustomerSummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCustomerSummary(customerId).then(setData).catch((e) => setError(e.message));
  }, [customerId]);

  if (error) return <div className="page"><ErrorState message={error} /></div>;
  if (!data) return <div className="page"><LoadingState /></div>;

  const { customer, summary, requests, complaints } = data;

  return (
    <div className="page">
      <Breadcrumbs items={[{ label: "Dashboard", to: "/dashboard" }, { label: "Customer 360" }]} />
      {/* <span className="eyebrow">Customer 360</span> */}
      <h1>{customer.full_name}</h1>
      <div className="customer-meta-row">
        {customer.email && <span><Mail size={14} /> {customer.email}</span>}
        {customer.phone && <span><Phone size={14} /> {customer.phone}</span>}
        {customer.location && <span><MapPin size={14} /> {customer.location}</span>}
      </div>

      <div className="kpi-grid">
        <KpiCard label="Total requests" value={summary.total_requests} />
        <KpiCard label="Open requests" value={summary.open_requests} />
        <KpiCard label="Resolved" value={summary.resolved_requests} />
        <KpiCard label="Closed" value={summary.closed_requests} />
        <KpiCard label="Total complaints" value={summary.total_complaints} />
        <KpiCard label="Open complaints" value={summary.open_complaints} highlight={summary.open_complaints > 0} />
        <KpiCard label="SLA compliance" value={summary.sla_compliance_pct != null ? `${summary.sla_compliance_pct}%` : "—"} />
        <KpiCard label="Avg. resolution" value={summary.average_resolution_hours != null ? `${summary.average_resolution_hours}h` : "—"} />
      </div>

      <div className="detail-card" style={{ marginBottom: 18 }}>
        <h2>Request history</h2>
        {requests.length === 0 && <EmptyState message="No service requests yet." />}
        {requests.length > 0 && (
          <table className="data-table">
            <thead><tr><th>Reference</th><th>Category</th><th>Priority</th><th>Status</th><th>Created</th></tr></thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id}>
                  <td><Link to={`/requests/${r.id}`}>{r.reference_number}</Link></td>
                  <td>{r.category_name}</td>
                  <td><PriorityBadge priority={r.priority} /></td>
                  <td><StatusBadge status={r.status} /></td>
                  <td>{formatPkDate(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="detail-card">
        <h2>Complaint history</h2>
        {complaints.length === 0 && <EmptyState message="No complaints on record." />}
        {complaints.length > 0 && (
          <table className="data-table">
            <thead><tr><th>Reference</th><th>Category</th><th>Severity</th><th>Status</th><th>Resolution</th></tr></thead>
            <tbody>
              {complaints.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/complaints/${c.id}`}>{c.reference_number}</Link></td>
                  <td>{c.category.replace(/_/g, " ")}</td>
                  <td>{c.severity}</td>
                  <td><StatusBadge status={c.status} /></td>
                  <td className="truncate">{c.resolution || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function KpiCard({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <div className={`kpi-card${highlight ? " kpi-highlight" : ""}`}>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}
