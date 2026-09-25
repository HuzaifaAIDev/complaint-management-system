import React, { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Check, X as XIcon, Layers } from "lucide-react";
import { ServiceCategory, SlaRule, Priority } from "../types";
import { listCategories, listSlaRules, updateSlaRule, deleteSlaRule } from "../services/resourceService";
import { apiPost } from "../services/apiClient";
import { LoadingState, ErrorState } from "../components/Common";
import { ApiError } from "../services/apiClient";
import { useToast } from "../context/ToastContext";
import { useConfirm } from "../context/ConfirmContext";
import Breadcrumbs from "../components/Breadcrumbs";

const ALL_PRIORITIES: Priority[] = ["low", "medium", "high", "urgent"];

export default function AdminCategoriesPage() {
  const [categories, setCategories] = useState<ServiceCategory[]>([]);
  const [rules, setRules] = useState<SlaRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const toast = useToast();

  const load = () => {
    setLoading(true);
    Promise.all([listCategories(false), listSlaRules()])
      .then(([c, r]) => { setCategories(c.items); setRules(r.items); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div className="page">
      <Breadcrumbs items={[{ label: "Dashboard", to: "/dashboard" }, { label: "Administration" }, { label: "Service Categories" }]} />
      {/* <span className="eyebrow">Administration</span> */}
      <div className="page-header">
        <h1><span className="page-header-icon"><Layers size={17} /></span> Service Catalog</h1>
        <button className="btn-primary" onClick={() => setShowCreate((v) => !v)}>
          <Plus size={15} /> {showCreate ? "Cancel" : "New category"}
        </button>
      </div>

      {showCreate && <CreateCategoryForm onCreated={() => { setShowCreate(false); load(); toast.success("Service category created successfully."); }} />}

      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && categories.map((c) => (
        <CategoryCard key={c.id} category={c} rules={rules.filter((r) => r.category_id === c.id)} onChanged={load} />
      ))}
    </div>
  );
}

function CategoryCard({ category, rules, onChanged }: { category: ServiceCategory; rules: SlaRule[]; onChanged: () => void }) {
  const toast = useToast();
  const configuredPriorities = new Set(rules.map((r) => r.priority));
  const availablePriorities = ALL_PRIORITIES.filter((p) => !configuredPriorities.has(p));
  const allConfigured = availablePriorities.length === 0;

  return (
    <div className="detail-card" style={{ marginBottom: 16 }}>
      <h2>{category.name} {!category.is_active && <span className="muted">(inactive)</span>}</h2>
      {category.description && <p className="muted">{category.description}</p>}
      <p className="muted">Default SLA: {category.default_sla_hours}h</p>

      <h3 style={{ marginTop: 16 }}>SLA rules</h3>
      {rules.length === 0 && <p className="muted">No SLA rules configured for this category yet.</p>}
      {rules.length > 0 && (
        <table className="data-table" style={{ marginTop: 8 }}>
          <thead><tr><th>Priority</th><th>Response (h)</th><th>Resolution (h)</th><th></th></tr></thead>
          <tbody>
            {rules.map((r) => (
              <SlaRuleRow key={r.id} rule={r} onChanged={onChanged} />
            ))}
          </tbody>
        </table>
      )}

      {allConfigured ? (
        <p className="sla-all-configured">All SLA priorities are configured for this category.</p>
      ) : (
        <AddSlaRuleForm
          categoryId={category.id}
          availablePriorities={availablePriorities}
          onCreated={() => { onChanged(); toast.success("SLA rule created successfully."); }}
        />
      )}
    </div>
  );
}

function SlaRuleRow({ rule, onChanged }: { rule: SlaRule; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [response, setResponse] = useState(String(rule.response_hours));
  const [resolution, setResolution] = useState(String(rule.resolution_hours));
  const [saving, setSaving] = useState(false);
  const toast = useToast();
  const confirm = useConfirm();

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateSlaRule(rule.id, { response_hours: Number(response), resolution_hours: Number(resolution) });
      toast.success("SLA rule updated successfully.");
      setEditing(false);
      onChanged();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to update SLA rule.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    const ok = await confirm({
      title: "Delete SLA Rule?",
      description: `Are you sure you want to delete the ${rule.priority} priority rule? This cannot be undone.`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    try {
      await deleteSlaRule(rule.id);
      toast.success("SLA rule deleted.");
      onChanged();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to delete SLA rule.");
    }
  };

  if (editing) {
    return (
      <tr>
        <td style={{ textTransform: "capitalize" }}>{rule.priority}</td>
        <td><input type="number" min={1} value={response} onChange={(e) => setResponse(e.target.value)} style={{ width: 80, marginBottom: 0 }} /></td>
        <td><input type="number" min={1} value={resolution} onChange={(e) => setResolution(e.target.value)} style={{ width: 80, marginBottom: 0 }} /></td>
        <td>
          <div className="btn-row" style={{ marginTop: 0 }}>
            <button className="btn-secondary" disabled={saving} onClick={handleSave} aria-label="Save"><Check size={14} /></button>
            <button className="btn-secondary" disabled={saving} onClick={() => setEditing(false)} aria-label="Cancel"><XIcon size={14} /></button>
          </div>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td style={{ textTransform: "capitalize" }}>{rule.priority}</td>
      <td>{rule.response_hours}</td>
      <td>{rule.resolution_hours}</td>
      <td>
        <div className="btn-row" style={{ marginTop: 0 }}>
          <button className="btn-link" onClick={() => setEditing(true)}><Pencil size={13} /></button>
          <button className="btn-link" style={{ color: "var(--breach)" }} onClick={handleDelete}><Trash2 size={13} /></button>
        </div>
      </td>
    </tr>
  );
}

function CreateCategoryForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState({ name: "", description: "", default_sla_hours: "72" });
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    setSubmitting(true);
    try {
      await apiPost("/service-categories", { ...form, default_sla_hours: Number(form.default_sla_hours) });
      onCreated();
    } catch (err) {
      if (err instanceof ApiError && err.fields) setFieldErrors(err.fields);
      else setError(err instanceof ApiError ? err.message : "Could not create category");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      {error && <div className="alert alert-error">{error}</div>}
      <label>
        Name
        <input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required />
        {fieldErrors.name && <span className="field-error">{fieldErrors.name}</span>}
      </label>
      <label>Description<textarea value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} /></label>
      <label>Default SLA hours<input type="number" min={1} value={form.default_sla_hours} onChange={(e) => setForm((f) => ({ ...f, default_sla_hours: e.target.value }))} /></label>
      <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? "Creating..." : "Create category"}</button>
    </form>
  );
}

function AddSlaRuleForm({ categoryId, availablePriorities, onCreated }: {
  categoryId: number; availablePriorities: Priority[]; onCreated: () => void;
}) {
  const [priority, setPriority] = useState<Priority>(availablePriorities[0]);
  const [responseHours, setResponseHours] = useState("8");
  const [resolutionHours, setResolutionHours] = useState("48");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const toast = useToast();

  // Keep the selected priority valid as rules are added/removed elsewhere.
  useEffect(() => {
    if (!availablePriorities.includes(priority)) {
      setPriority(availablePriorities[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availablePriorities.join(",")]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await apiPost("/sla-rules", {
        category_id: categoryId, priority,
        response_hours: Number(responseHours), resolution_hours: Number(resolutionHours),
      });
      onCreated();
    } catch (err) {
      if (err instanceof ApiError && err.fields) {
        // Backend correctly rejects duplicate category+priority - surface it plainly.
        const message = Object.values(err.fields)[0] || err.message;
        setError(message);
        toast.error("Unable to create SLA rule. " + message);
      } else {
        const message = err instanceof ApiError ? err.message : "Could not create SLA rule";
        setError(message);
        toast.error(message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="sla-add-form" onSubmit={handleSubmit}>
      {error && <div className="field-error" style={{ marginBottom: 8 }}>{error}</div>}
      <div className="btn-row" style={{ marginTop: 8 }}>
        <select value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
          {availablePriorities.map((p) => <option key={p} value={p}>{p[0].toUpperCase() + p.slice(1)}</option>)}
        </select>
        <input type="number" min={1} placeholder="Response h" value={responseHours} onChange={(e) => setResponseHours(e.target.value)} style={{ width: 100 }} />
        <input type="number" min={1} placeholder="Resolution h" value={resolutionHours} onChange={(e) => setResolutionHours(e.target.value)} style={{ width: 110 }} />
        <button type="submit" className="btn-secondary" disabled={submitting}>
          <Plus size={14} /> Add rule
        </button>
      </div>
    </form>
  );
}
