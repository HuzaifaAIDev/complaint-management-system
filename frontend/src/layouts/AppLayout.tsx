import React, { useState } from "react";
import { Link, NavLink, Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  LayoutDashboard, ClipboardList, MessageSquareWarning, Users,
  Layers, ScrollText, LogOut, Radar, LucideIcon, Gauge, UsersRound, Kanban, UserCog2,
  Menu, X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Role } from "../types";
import GlobalSearch from "../components/GlobalSearch";
import NotificationsBell from "../components/NotificationsBell";
import CommandPalette from "../components/CommandPalette";
import ThemeToggle from "../components/ThemeToggle";
import { getHomePath } from "../utils/roleHome";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

const NAV_BY_ROLE: Record<Role, NavItem[]> = {
  customer: [
    { to: "/requests", label: "My Complaints", icon: ClipboardList },
    { to: "/complaints", label: "Service Feedback", icon: MessageSquareWarning },
  ],
  agent: [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/requests", label: "My Complaints", icon: ClipboardList },
    { to: "/complaints", label: "Service Feedback", icon: MessageSquareWarning },
    { to: "/sla-monitoring", label: "SLA Monitoring", icon: Gauge },
  ],
  supervisor: [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/requests", label: "Complaints", icon: ClipboardList },
    { to: "/requests/board", label: "Kanban Board", icon: Kanban },
    { to: "/complaints", label: "Service Feedback", icon: MessageSquareWarning },
    { to: "/sla-monitoring", label: "SLA Monitoring", icon: Gauge },
    { to: "/agents/workload", label: "Agent Workload", icon: UsersRound },
    { to: "/admin/users", label: "Agents & Users", icon: Users },
  ],
  admin: [
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/requests", label: "Complaints", icon: ClipboardList },
    { to: "/requests/board", label: "Kanban Board", icon: Kanban },
    { to: "/complaints", label: "Service Feedback", icon: MessageSquareWarning },
    { to: "/sla-monitoring", label: "SLA Monitoring", icon: Gauge },
    { to: "/agents/workload", label: "Agent Workload", icon: UsersRound },
    { to: "/admin/users", label: "Users & Agents", icon: Users },
    { to: "/admin/categories", label: "Categories", icon: Layers },
    { to: "/admin/audit-logs", label: "Audit Logs", icon: ScrollText },
  ],
};

function initials(name: string) {
  return name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const navItems = user ? NAV_BY_ROLE[user.role] || [] : [];

  React.useEffect(() => { setMobileNavOpen(false); }, [location.pathname]);

  return (
    <div className="app-shell">
      {mobileNavOpen && <div className="sidebar-scrim" onClick={() => setMobileNavOpen(false)} />}
      <aside className={`sidebar${mobileNavOpen ? " sidebar-open" : ""}`}>
        <div className="sidebar-brand-row">
          <Link to={user ? getHomePath(user.role) : "/"} className="sidebar-brand">
            <span className="sidebar-brand-mark"><Radar size={16} color="#fff" /></span>
            <span className="sidebar-brand-text">
              Dispatch
              <small>Service &amp; Complaints</small>
            </span>
          </Link>
          <button className="sidebar-close" onClick={() => setMobileNavOpen(false)} aria-label="Close menu"><X size={18} /></button>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "sidebar-link active" : "sidebar-link")}
            >
              <item.icon size={17} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {user && (
          <div className="sidebar-footer">
            <Link to="/profile" className="sidebar-user sidebar-user-link">
              <span className="sidebar-avatar">{initials(user.name)}</span>
              <div>
                <div className="sidebar-user-name">{user.name}</div>
                <div className="sidebar-user-role">{user.role}</div>
              </div>
              <UserCog2 size={14} className="sidebar-user-settings-icon" />
            </Link>
            <button className="sidebar-logout" onClick={handleLogout}>
              <LogOut size={15} /> Log out
            </button>
            <div className="sidebar-hint">Press <kbd>Ctrl</kbd>+<kbd>K</kbd> for commands</div>
          </div>
        )}
      </aside>

      <main className="app-content">
        <div className="topbar">
          <button className="mobile-menu-btn" onClick={() => setMobileNavOpen(true)} aria-label="Open menu"><Menu size={19} /></button>
          <GlobalSearch />
          <div className="topbar-actions">
            <ThemeToggle />
            <NotificationsBell />
          </div>
        </div>
        <Outlet />
      </main>
      {user && <CommandPalette role={user.role} />}
    </div>
  );
}
