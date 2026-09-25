import React, { useEffect, useRef, useState, useCallback } from "react";
import { Bell, CheckCheck } from "lucide-react";
import { listNotifications, markNotificationRead, markAllNotificationsRead } from "../services/resourceService";
import { Notification } from "../types";
import { formatPkDateTime } from "../utils/datetime";

export default function NotificationsBell() {
  const [items, setItems] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const unreadCount = items.filter((n) => !n.is_read).length;

  const load = useCallback(() => {
    listNotifications(false).then((res) => setItems(res.items)).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const interval = window.setInterval(load, 30000);
    return () => window.clearInterval(interval);
  }, [load]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleItemClick = async (n: Notification) => {
    if (!n.is_read) {
      await markNotificationRead(n.id);
      load();
    }
  };

  const handleMarkAll = async () => {
    await markAllNotificationsRead();
    load();
  };

  return (
    <div className="notif-bell" ref={containerRef}>
      <button className="notif-trigger" onClick={() => setOpen((v) => !v)} aria-label={`Notifications, ${unreadCount} unread`}>
        <Bell size={18} />
        {unreadCount > 0 && <span className="notif-badge">{unreadCount > 9 ? "9+" : unreadCount}</span>}
      </button>
      {open && (
        <div className="notif-dropdown" role="menu">
          <div className="notif-dropdown-header">
            <span>Notifications</span>
            {unreadCount > 0 && (
              <button className="btn-link" onClick={handleMarkAll}><CheckCheck size={13} /> Mark all read</button>
            )}
          </div>
          <div className="notif-list">
            {items.length === 0 && <div className="gsr-empty">No notifications yet.</div>}
            {items.map((n) => (
              <button key={n.id} className={`notif-item${n.is_read ? "" : " notif-item-unread"}`} onClick={() => handleItemClick(n)}>
                <span className="notif-dot" />
                <div>
                  <div className="notif-message">{n.message}</div>
                  <div className="notif-time">{formatPkDateTime(n.created_at)}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
