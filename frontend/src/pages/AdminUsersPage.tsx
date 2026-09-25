import React, { useEffect, useState } from "react";
import { Users as UsersIcon, Tag, X as XIcon, Plus } from "lucide-react";
import { User, Role, ServiceCategory, AgentCategoryLink } from "../types";
import { listUsers, listCategories, listAgentCategories, addAgentCategory, removeAgentCategory } from "../services/resourceService";
import { apiPatch, apiPost } from "../services/apiClient";
import { LoadingState, ErrorState } from "../components/Common";
import { ApiError } from "../services/apiClient";
import { useToast } from "../context/ToastContext";
import Breadcrumbs from "../components/Breadcrumbs";

const ROLES: Role[] = ["customer", "agent", "supervisor", "admin"];

export default function AdminUsersPage() {
  const [items, setItems] = useState<User[]>([]);
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [expandedAgentId, setExpandedAgentId] = useState<number | null>(null);
  const toast = useToast();

  const load = () => {
    setLoading(true);
    Promise.all([listUsers(), listCategories(true)])
      .then(([u, c]) => { setItems(u.items); setCategories(c.items); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const toggleActive = async (user: User) => {
    await apiPatch(`/users/${user.id}`, { is_active: !user.is_active });
    load();
  };

  return (
    <div className="page">
      <Breadcrumbs items={[{ label: "Dashboard", to: "/dashboard" }, { label: "Users & Agents" }]} />
      <div className="page-header">
        <h1><span className="page-header-icon"><UsersIcon size={17} /></span> Users &amp; Agents</h1>
        <button className="btn-primary" onClick={() => setShowCreate((v) => !v)}>{showCreate ? "Cancel" : "New user"}</button>
      </div>
      <p className="muted" style={{ marginTop: -6, marginBottom: 20 }}>
        Manage accounts and, for agents, the categories they're assigned complaints in.
      </p>

      {showCreate && <CreateUserForm onCreated={() => { setShowCreate(false); load(); toast.success("User created successfully."); }} />}

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && (
        <table className="data-table">
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Categories</th><th>Actions</th></tr></thead>
          <tbody>
            {items.map((u) => (
              <React.Fragment key={u.id}>
                <tr>
                  <td>{u.name}</td>
                  <td>{u.email}</td>
                  <td style={{ textTransform: "capitalize" }}>{u.role}</td>
                  <td>{u.is_active ? "Active" : "Disabled"}</td>
                  <td>
                    {u.role === "agent" ? (
                      <button className="btn-link" onClick={() => setExpandedAgentId(expandedAgentId === u.id ? null : u.id)}>
                        <Tag size={13} /> {expandedAgentId === u.id ? "Hide" : "Manage"}
                      </button>
                    ) : <span className="muted">—</span>}
                  </td>
                  <td><button className="btn-link" onClick={() => toggleActive(u)}>{u.is_active ? "Disable" : "Enable"}</button></td>
                </tr>
                {u.role === "agent" && expandedAgentId === u.id && (
                  <tr>
                    <td colSpan={6} style={{ background: "var(--canvas)" }}>
                      <AgentCategoryManager agent={u} categories={categories} />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

/**
 * Admin-only editor for which categories/skills an agent belongs to.
 * This is the data that powers the category-filtered agent dropdown in
 * the assignment workflow - an agent with no categories here will never
 * show up as an assignable option for any complaint.
 */
function AgentCategoryManager({ agent, categories }: { agent: User; categories: ServiceCategory[] }) {
  const [links, setLinks] = useState<AgentCategoryLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [addingCategoryId, setAddingCategoryId] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const load = () => {
    setLoading(true);
    listAgentCategories(agent.id).then((res) => setLinks(res.items)).finally(() => setLoading(false));
  };

  useEffect(load, [agent.id]);

  const linkedIds = new Set(links.map((l) => l.category_id));
  const availableCategories = categories.filter((c) => !linkedIds.has(c.id));

  const handleAdd = async () => {
    if (!addingCategoryId) return;
    setBusy(true);
    try {
      await addAgentCategory(agent.id, Number(addingCategoryId));
      setAddingCategoryId("");
      load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to add category.");
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (categoryId: number) => {
    setBusy(true);
    try {
      await removeAgentCategory(agent.id, categoryId);
      load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to remove category.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ padding: "12px 4px" }}>
      <div className="assign-step-label" style={{ marginBottom: 8 }}>Categories for {agent.name}</div>
      {loading ? (
        <LoadingState label="Loading categories..." />
      ) : (
        <>
          <div className="btn-row" style={{ marginTop: 0, flexWrap: "wrap" }}>
            {links.length === 0 && <span className="muted">Not assigned to any category yet — this agent will not appear in the assignment picker.</span>}
            {links.map((l) => (
              <span key={l.id} className="category-chip">
                {l.category_name}
                <button className="category-chip-remove" disabled={busy} onClick={() => handleRemove(l.category_id)} aria-label={`Remove ${l.category_name}`}>
                  <XIcon size={12} />
                </button>
              </span>
            ))}
          </div>

          {availableCategories.length > 0 && (
            <div className="btn-row" style={{ marginTop: 10 }}>
              <select value={addingCategoryId} onChange={(e) => setAddingCategoryId(e.target.value)} style={{ maxWidth: 220 }}>
                <option value="">Add category...</option>
                {availableCategories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <button className="btn-secondary" disabled={!addingCategoryId || busy} onClick={handleAdd}>
                <Plus size={14} /> Add
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function CreateUserForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "agent" as Role });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiPost("/users", form);
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create user");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      {error && <div className="alert alert-error">{error}</div>}
      <label>Name<input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required /></label>
      <label>Email<input type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} required /></label>
      <label>Password<input type="password" value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} required minLength={10} /></label>
      <label>
        Role
        <select value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value as Role }))}>
          {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </label>
      <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? "Creating..." : "Create user"}</button>
    </form>
  );
}
