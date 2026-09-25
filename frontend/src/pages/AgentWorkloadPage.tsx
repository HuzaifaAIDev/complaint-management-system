import React, { useEffect, useState } from "react";
import { UsersRound } from "lucide-react";
import { AgentWorkload } from "../types";
import { getAgentWorkload } from "../services/resourceService";
import { LoadingState, ErrorState, EmptyState } from "../components/Common";

function workloadTone(w: AgentWorkload): "high" | "medium" | "low" {
  const active = w.open + w.in_progress;
  if (w.sla_breached > 0 || active >= 8) return "high";
  if (w.sla_at_risk > 0 || active >= 4) return "medium";
  return "low";
}

export default function AgentWorkloadPage() {
  const [items, setItems] = useState<AgentWorkload[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAgentWorkload().then((res) => setItems(res.items)).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      {/* <span className="eyebrow">Team operations</span> */}
      <h1><span className="page-header-icon"><UsersRound size={17} /></span> Agent Workload</h1>
      <p className="muted" style={{ marginBottom: 20 }}>Identify overloaded agents and SLA risk concentration across the team.</p>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && items.length === 0 && <EmptyState message="No active agents found." />}

      {!loading && items.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Agent</th><th>Load</th><th>Open</th><th>In progress</th><th>SLA risk</th>
              <th>SLA breached</th><th>Completed</th><th>Avg. resolution</th><th>SLA compliance</th>
            </tr>
          </thead>
          <tbody>
            {items.map((w) => {
              const tone = workloadTone(w);
              return (
                <tr key={w.agent_id}>
                  <td>{w.agent_name}</td>
                  <td><span className={`workload-dot workload-${tone}`} /> <span className="workload-label">{tone}</span></td>
                  <td>{w.open}</td>
                  <td>{w.in_progress}</td>
                  <td>{w.sla_at_risk > 0 ? <span style={{ color: "var(--warning)", fontWeight: 600 }}>{w.sla_at_risk}</span> : w.sla_at_risk}</td>
                  <td>{w.sla_breached > 0 ? <span style={{ color: "var(--breach)", fontWeight: 600 }}>{w.sla_breached}</span> : w.sla_breached}</td>
                  <td>{w.completed}</td>
                  <td>{w.average_resolution_hours != null ? `${w.average_resolution_hours}h` : "—"}</td>
                  <td>{w.sla_compliance_pct != null ? `${w.sla_compliance_pct}%` : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
