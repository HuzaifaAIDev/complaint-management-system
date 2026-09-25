import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  LayoutDashboard, ClipboardList, MessageSquareWarning, Users, Layers,
  ScrollText, Gauge, UsersRound, Kanban, Plus, User as UserIcon, Search, LucideIcon,
} from "lucide-react";
import { Role } from "../types";

interface Command {
  id: string;
  label: string;
  hint?: string;
  icon: LucideIcon;
  action: (navigate: ReturnType<typeof useNavigate>) => void;
  roles?: Role[];
}

const COMMANDS: Command[] = [
  { id: "dashboard", label: "Open Dashboard", icon: LayoutDashboard, action: (nav) => nav("/dashboard"), roles: ["admin", "supervisor", "agent"] },
  { id: "requests", label: "Open Requests", icon: ClipboardList, action: (nav) => nav("/requests") },
  { id: "new-request", label: "Submit a Complaint", icon: Plus, action: (nav) => nav("/requests/new"), roles: ["customer"] },
  { id: "complaints", label: "Open Complaints", icon: MessageSquareWarning, action: (nav) => nav("/complaints") },
  { id: "new-complaint", label: "Create Complaint", icon: Plus, action: (nav) => nav("/complaints/new"), roles: ["customer"] },
  { id: "sla", label: "View SLA Breaches & Monitoring", icon: Gauge, action: (nav) => nav("/sla-monitoring"), roles: ["admin", "supervisor", "agent"] },
  { id: "board", label: "Open Kanban Board", icon: Kanban, action: (nav) => nav("/requests/board"), roles: ["admin", "supervisor", "agent"] },
  { id: "workload", label: "Open Agent Workload", icon: UsersRound, action: (nav) => nav("/agents/workload"), roles: ["admin", "supervisor"] },
  { id: "users", label: "Manage Users", icon: Users, action: (nav) => nav("/admin/users"), roles: ["admin", "supervisor"] },
  { id: "catalog", label: "Open Service Catalog", icon: Layers, action: (nav) => nav("/admin/categories"), roles: ["admin"] },
  { id: "audit", label: "Open Audit Logs", icon: ScrollText, action: (nav) => nav("/admin/audit-logs"), roles: ["admin", "supervisor"] },
  { id: "profile", label: "Open Profile & Settings", icon: UserIcon, action: (nav) => nav("/profile") },
];

export default function CommandPalette({ role }: { role: Role }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    function handleKeydown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, []);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  // Command visibility is a UX convenience - every command just navigates
  // to a route that is itself gated by ProtectedRoute + backend
  // authorization. The palette can never grant access on its own.
  const available = useMemo(
    () => COMMANDS.filter((c) => !c.roles || c.roles.includes(role)),
    [role]
  );
  const filtered = query.trim()
    ? available.filter((c) => c.label.toLowerCase().includes(query.trim().toLowerCase()))
    : available;

  if (!open) return null;

  const run = (cmd: Command) => {
    cmd.action(navigate);
    setOpen(false);
  };

  return (
    <div className="modal-overlay" role="presentation" onClick={() => setOpen(false)}>
      <div className="palette-card" role="dialog" aria-modal="true" aria-label="Command palette" onClick={(e) => e.stopPropagation()}>
        <div className="palette-search">
          <Search size={16} />
          <input
            autoFocus
            placeholder="Type a command..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <kbd>Esc</kbd>
        </div>
        <div className="palette-list">
          {filtered.length === 0 && <div className="gsr-empty">No matching commands.</div>}
          {filtered.map((c) => (
            <button key={c.id} className="palette-item" onClick={() => run(c)}>
              <c.icon size={15} />
              {c.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
