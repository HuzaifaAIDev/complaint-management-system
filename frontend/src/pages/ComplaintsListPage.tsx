import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Complaint } from "../types";
import { listComplaints } from "../services/resourceService";
import { LoadingState, ErrorState, EmptyState, StatusBadge } from "../components/Common";
import { useAuth } from "../context/AuthContext";
import { Plus, Download, RotateCcw, ChevronLeft, ChevronRight, MessageSquareWarning } from "lucide-react";
import { API_BASE_URL } from "../services/apiClient";
import { formatPkDate } from "../utils/datetime";

const STATUS_OPTIONS = ["", "open", "in_review", "escalated", "resolved", "closed", "reopened"];
const SEVERITY_OPTIONS = ["", "minor", "moderate", "major", "critical"];
const PAGE_SIZE = 25;
const emptyFilters = { search: "", status: "", severity: "" };

export default function ComplaintsListPage() {
  const { user } = useAuth();
  const isStaff = user && ["admin", "supervisor", "agent"].includes(user.role);
  const isCustomer = user?.role === "customer";
  const [items, setItems] = useState<Complaint[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState(emptyFilters);

  const load = useCallback(() => {
    setLoading(true);
    listComplaints({
      search: appliedFilters.search || undefined,
      status: appliedFilters.status || undefined,
      severity: appliedFilters.severity || undefined,
      page, page_size: PAGE_SIZE,
    })
      .then((res) => { setItems(res.items); setTotal(res.total); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [appliedFilters, page]);

  useEffect(() => { load(); }, [load]);

  const applyFilters = () => { setPage(1); setAppliedFilters(filters); };
  const resetFilters = () => { setFilters(emptyFilters); setAppliedFilters(emptyFilters); setPage(1); };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const rangeStart = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(page * PAGE_SIZE, total);

  const exportUrl = (() => {
    const params = new URLSearchParams();
    if (appliedFilters.status) params.set("status", appliedFilters.status);
    if (appliedFilters.severity) params.set("severity", appliedFilters.severity);
    return `${API_BASE_URL}/complaints/export?${params.toString()}`;
  })();

  return (
    <div className="page">
      <div className="page-header">
        <h1><span className="page-header-icon"><MessageSquareWarning size={17} /></span> {user?.role === "customer" ? "Feedback" : "Feedback"}</h1>
        <div className="btn-row" style={{ marginTop: 0 }}>
          {isStaff && <a className="btn-secondary" href={exportUrl}><Download size={15} /> Export CSV</a>}
          {user?.role === "customer" && <Link className="btn-primary" to="/complaints/new"><Plus size={15} /> Lodge a feedback</Link>}
        </div>
      </div>

      {!isCustomer && (
        <div className="filter-panel">
          <div className="filter-grid">
            <input placeholder="Search reference, description..." value={filters.search} onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))} />
            <select value={filters.status} onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}>
              {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s ? s.replace(/_/g, " ") : "All statuses"}</option>)}
            </select>
            <select value={filters.severity} onChange={(e) => setFilters((f) => ({ ...f, severity: e.target.value }))}>
              {SEVERITY_OPTIONS.map((s) => <option key={s} value={s}>{s || "All severities"}</option>)}
            </select>
          </div>
          <div className="btn-row">
            <button className="btn-primary" onClick={applyFilters}>Apply Filters</button>
            <button className="btn-secondary" onClick={resetFilters}><RotateCcw size={14} /> Reset Filters</button>
          </div>
        </div>
      )}

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && items.length === 0 && (
        <EmptyState message={isCustomer ? "You haven't filed any complaints yet." : "No complaints found. Try changing your filters."} />
      )}

      {!loading && items.length > 0 && (
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>Reference</th>
                {!isCustomer && <th>Customer</th>}
                <th>Category</th><th>Severity</th><th>Status</th><th>Filed</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id}>
                  <td><Link to={`/complaints/${c.id}`}>{c.reference_number}</Link></td>
                  {!isCustomer && <td>{c.customer_name || "—"}</td>}
                  <td>{c.category.replace(/_/g, " ")}</td>
                  <td>{c.severity}</td>
                  <td><StatusBadge status={c.status} /></td>
                  <td>{formatPkDate(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="pagination-bar">
            <span className="muted">Showing {rangeStart}–{rangeEnd} of {total} results</span>
            <div className="pagination-controls">
              <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft size={14} /></button>
              <span className="muted">Page {page} of {totalPages}</span>
              <button className="btn-secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}><ChevronRight size={14} /></button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
