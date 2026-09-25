import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { ServiceRequest, ServiceCategory, User } from "../types";
import { listRequests } from "../services/requestService";
import { listCategories, listUsers } from "../services/resourceService";
import { LoadingState, ErrorState, EmptyState, StatusBadge, PriorityBadge, SlaStateBadge } from "../components/Common";
import { formatPkDate } from "../utils/datetime";
import { useAuth } from "../context/AuthContext";
import { Plus, Download, RotateCcw, ChevronLeft, ChevronRight, ClipboardList } from "lucide-react";
import { API_BASE_URL } from "../services/apiClient";

const STATUS_OPTIONS = ["", "submitted", "assigned", "scheduled", "in_progress", "pending_customer", "resolved", "closed", "reopened"];
const PRIORITY_OPTIONS = ["", "low", "medium", "high", "urgent"];
const SLA_OPTIONS = ["", "within_sla", "at_risk", "breached"];
const SORT_OPTIONS = [
  { value: "-created_at", label: "Newest first" },
  { value: "created_at", label: "Oldest first" },
  { value: "-sla_resolution_deadline", label: "SLA deadline (soonest last)" },
  { value: "sla_resolution_deadline", label: "SLA deadline (soonest first)" },
  { value: "-priority", label: "Priority (high first)" },
];
const PAGE_SIZE = 25;

const emptyFilters = { search: "", status: "", priority: "", category_id: "", assigned_agent_id: "", sla_status: "", date_from: "", date_to: "" };

export default function RequestsListPage() {
  const { user } = useAuth();
  const isStaff = user && ["admin", "supervisor", "agent"].includes(user.role);
  const isCustomer = user?.role === "customer";
  const [items, setItems] = useState<ServiceRequest[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState(emptyFilters);
  const [sort, setSort] = useState("-created_at");
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [agents, setAgents] = useState<User[]>([]);

  useEffect(() => {
    listCategories(false).then((res) => setCategories(res.items)).catch(() => {});
    if (isStaff) listUsers("agent").then((res) => setAgents(res.items)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    listRequests({
      search: appliedFilters.search || undefined,
      status: appliedFilters.status || undefined,
      priority: appliedFilters.priority || undefined,
      category_id: appliedFilters.category_id || undefined,
      assigned_agent_id: appliedFilters.assigned_agent_id || undefined,
      sla_status: appliedFilters.sla_status || undefined,
      date_from: appliedFilters.date_from || undefined,
      date_to: appliedFilters.date_to || undefined,
      sort,
      page,
      page_size: PAGE_SIZE,
    })
      .then((res) => { setItems(res.items); setTotal(res.total); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [appliedFilters, sort, page]);

  useEffect(() => { load(); }, [load]);

  const applyFilters = () => { setPage(1); setAppliedFilters(filters); };
  const resetFilters = () => { setFilters(emptyFilters); setAppliedFilters(emptyFilters); setPage(1); };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const rangeStart = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(page * PAGE_SIZE, total);

  const exportUrl = (() => {
    const params = new URLSearchParams();
    if (appliedFilters.status) params.set("status", appliedFilters.status);
    if (appliedFilters.priority) params.set("priority", appliedFilters.priority);
    if (appliedFilters.category_id) params.set("category_id", appliedFilters.category_id);
    if (appliedFilters.date_from) params.set("date_from", appliedFilters.date_from);
    if (appliedFilters.date_to) params.set("date_to", appliedFilters.date_to);
    return `${API_BASE_URL}/service-requests/export?${params.toString()}`;
  })();

  return (
    <div className="page">
      <div className="page-header">
        <h1><span className="page-header-icon"><ClipboardList size={17} /></span> {user?.role === "customer" ? "My Requests" : "Service Requests"}</h1>
        <div className="btn-row" style={{ marginTop: 0 }}>
          {isStaff && <a className="btn-secondary" href={exportUrl}><Download size={15} /> Export CSV</a>}
          {user?.role === "customer" && <Link className="btn-primary" to="/requests/new"><Plus size={15} /> New request</Link>}
        </div>
      </div>

      {!isCustomer && (
        <div className="filter-panel">
          <div className="filter-grid">
            <input placeholder="Search reference, description..." value={filters.search} onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))} />
            <select value={filters.status} onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}>
              {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s ? s.replace(/_/g, " ") : "All statuses"}</option>)}
            </select>
            <select value={filters.priority} onChange={(e) => setFilters((f) => ({ ...f, priority: e.target.value }))}>
              {PRIORITY_OPTIONS.map((p) => <option key={p} value={p}>{p || "All priorities"}</option>)}
            </select>
            <select value={filters.category_id} onChange={(e) => setFilters((f) => ({ ...f, category_id: e.target.value }))}>
              <option value="">All categories</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            {isStaff && (
              <>
                <select value={filters.assigned_agent_id} onChange={(e) => setFilters((f) => ({ ...f, assigned_agent_id: e.target.value }))}>
                  <option value="">All agents</option>
                  {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
                <select value={filters.sla_status} onChange={(e) => setFilters((f) => ({ ...f, sla_status: e.target.value }))}>
                  {SLA_OPTIONS.map((s) => <option key={s} value={s}>{s ? s.replace(/_/g, " ") : "All SLA states"}</option>)}
                </select>
              </>
            )}
            <input type="date" value={filters.date_from} onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value }))} title="From date" />
            <input type="date" value={filters.date_to} onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value }))} title="To date" />
            <select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }}>
              {SORT_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
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
        <EmptyState message={isCustomer ? "You haven't submitted any requests yet." : "No requests found. Try changing your filters."} />
      )}

      {!loading && items.length > 0 && (
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>Reference</th>
                {!isCustomer && <th>Customer</th>}
                <th>Category</th><th>Priority</th><th>Status</th><th>SLA</th><th>Preferred date</th><th>Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id}>
                  <td><Link to={`/requests/${r.id}`}>{r.reference_number}</Link></td>
                  {!isCustomer && <td>{r.customer_name || "—"}</td>}
                  <td>{r.category_name || "—"}</td>
                  <td><PriorityBadge priority={r.priority} /></td>
                  <td><StatusBadge status={r.status} /></td>
                  <td><SlaStateBadge state={r.sla_state} /></td>
                  <td>{formatPkDate(r.preferred_date)}</td>
                  <td>{formatPkDate(r.created_at)}</td>
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
