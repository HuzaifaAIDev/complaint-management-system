import React, { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar,
} from "recharts";
import {
  MessageSquareWarning, ClipboardList, Radar as RadarIcon, Clock,
  ListChecks, Loader2, CheckCircle2, Gauge, ShieldAlert, TrendingUp, Timer, Star,
} from "lucide-react";
import { DashboardSummary, DashboardCharts, AuditLogEntry } from "../types";
import { getDashboardSummary, getDashboardCharts, getRecentActivity } from "../services/resourceService";
import { LoadingState, ErrorState } from "../components/Common";
import { formatPkDateTime, getPkHour } from "../utils/datetime";
import { useAuth } from "../context/AuthContext";

export default function DashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [charts, setCharts] = useState<DashboardCharts | null>(null);
  const [activity, setActivity] = useState<AuditLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role === "customer") return;
    getDashboardSummary().then(setSummary).catch((e) => setError(e.message));
    getDashboardCharts().then(setCharts).catch(() => {});
    getRecentActivity(10).then((res) => setActivity(res.items)).catch(() => {});
  }, [user]);

  // The analytics dashboard is a staff-only workspace - customers get a
  // simple "My Requests" list instead (see AppLayout / roleHome). This is
  // a defensive fallback in case something links here directly.
  if (user?.role === "customer") {
    return <Navigate to="/requests" replace />;
  }

  const hour = getPkHour();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="page">
      {/* <span className="eyebrow">Overview</span> */}
      <h1>{greeting}, {user?.name?.split(" ")[0]}</h1>
      <p className="page-header-sub">Here's what's happening across your workspace today.</p>
      {error && <ErrorState message={error} />}
      {!summary && !error && <LoadingState />}

      {summary && (
        <>
          <div className="kpi-grid">
            <KpiCard label="Total requests" value={summary.total_requests} icon={ClipboardList} color="#2f5dff" />
            <KpiCard label="Open requests" value={summary.open_requests} icon={ListChecks} color="#2f5dff" />
            <KpiCard label="In progress" value={summary.in_progress_requests} icon={Loader2} color="#b3760a" />
            <KpiCard label="Resolved today" value={summary.resolved_today} icon={CheckCircle2} color="#12876b" />
            <KpiCard label="SLA breached" value={summary.sla_breaches} highlight={summary.sla_breaches > 0} icon={ShieldAlert} color="#d1461f" />
            <KpiCard label="SLA at risk" value={summary.sla_at_risk} highlight={summary.sla_at_risk > 0} icon={Gauge} color="#b3760a" />
            <KpiCard label="SLA compliance" value={summary.sla_compliance_pct != null ? `${summary.sla_compliance_pct}%` : "—"} icon={TrendingUp} color="#12876b" />
            <KpiCard label="Feedback received" value={summary.unresolved_complaints} highlight={summary.unresolved_complaints > 0} icon={MessageSquareWarning} color="#d1461f" />
            <KpiCard label="Avg. response time" value={summary.average_response_hours != null ? `${summary.average_response_hours}h` : "—"} icon={Timer} color="#7c4dff" />
            <KpiCard label="Avg. resolution time" value={summary.average_resolution_hours != null ? `${summary.average_resolution_hours}h` : "—"} icon={Clock} color="#7c4dff" />
            <KpiCard label="Avg. satisfaction" value={summary.average_customer_satisfaction != null ? `${summary.average_customer_satisfaction} / 5` : "—"} icon={Star} color="#b3760a" />
          </div>

          {charts && (
            <div className="chart-grid">
              <div className="detail-card chart-card">
                <h2>Requests over the last 14 days</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={charts.requests_over_time}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d) => d.slice(5)} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={28} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                    <Line type="monotone" dataKey="count" stroke="#2f5dff" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="detail-card chart-card">
                <h2>Requests by status</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={charts.requests_by_status}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                    <XAxis dataKey="key" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={28} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                    <Bar dataKey="count" fill="#2f5dff" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="detail-card chart-card">
                <h2>Requests by priority</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={charts.requests_by_priority}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                    <XAxis dataKey="key" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} width={28} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                    <Bar dataKey="count" fill="#b3760a" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="detail-card chart-card">
                <h2>Requests by category</h2>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={charts.requests_by_category} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" />
                    <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="key" tick={{ fontSize: 11 }} width={110} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                    <Bar dataKey="count" fill="#12876b" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </>
      )}

      <div className="dash-lower-grid">
        <div className="quick-links">
          <Link className="btn-secondary" to="/requests"><ClipboardList size={15} /> View requests</Link>
          <Link className="btn-secondary" to="/complaints"><MessageSquareWarning size={15} /> View complaints</Link>
          <Link className="btn-secondary" to="/sla-monitoring"><RadarIcon size={15} /> SLA monitoring</Link>
        </div>

        {activity.length > 0 && (
          <div className="detail-card">
            <h2><Clock size={16} /> Recent activity</h2>
            <ul className="history-list">
              {activity.map((a) => (
                <li key={a.id}>
                  <strong>{a.action.replace(/_/g, " ")}</strong>
                  <span className="muted"> · {a.entity_type}{a.entity_id ? ` #${a.entity_id}` : ""} · {formatPkDateTime(a.created_at)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function KpiCard({ label, value, highlight, icon: Icon, color }: { label: string; value: string | number; highlight?: boolean; icon?: any; color?: string }) {
  return (
    <div className={`kpi-card${highlight ? " kpi-highlight" : ""}`}>
      {Icon && (
        <span className="kpi-icon" style={{ background: `${color}17`, color }}>
          <Icon size={16} />
        </span>
      )}
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}
