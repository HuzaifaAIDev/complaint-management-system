import React, { useEffect, useState } from "react";
import { ScrollText } from "lucide-react";
import { AuditLogEntry } from "../types";
import { listAuditLogs } from "../services/resourceService";
import { LoadingState, ErrorState, EmptyState } from "../components/Common";
import { formatPkDateTime } from "../utils/datetime";

export default function AdminAuditLogsPage() {
  const [items, setItems] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAuditLogs({ page_size: 100 }).then((res) => setItems(res.items)).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  return (
    <div className="page">
      <h1><span className="page-header-icon"><ScrollText size={17} /></span> Audit Logs</h1>
      <p className="page-header-sub">Read-only record of security-relevant and business-critical actions.</p>
      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && items.length === 0 && <EmptyState message="No audit entries yet." />}
      {!loading && items.length > 0 && (
        <table className="data-table">
          <thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Entity</th><th>Result</th></tr></thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id}>
                <td>{formatPkDateTime(a.created_at)}</td>
                <td>{a.user_id ?? "system"}</td>
                <td>{a.action}</td>
                <td>{a.entity_type}{a.entity_id ? ` #${a.entity_id}` : ""}</td>
                <td>{a.result}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
