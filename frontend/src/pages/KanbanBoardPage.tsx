import React, { useEffect, useState, useCallback } from "react";
import { Kanban } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { apiGet } from "../services/apiClient";
import { changeStatus } from "../services/requestService";
import { PriorityBadge, SlaStateBadge } from "../components/Common";
import { LoadingState, ErrorState } from "../components/Common";
import { useToast } from "../context/ToastContext";
import Breadcrumbs from "../components/Breadcrumbs";
import { ApiError } from "../services/apiClient";

interface BoardCard {
  id: number;
  reference_number: string;
  customer_name: string | null;
  category_name: string | null;
  priority: string;
  assigned_agent_name: string | null;
  sla_state: string | null;
}

interface BoardResponse {
  columns: Record<string, BoardCard[]>;
}

const COLUMN_ORDER = ["submitted", "assigned", "scheduled", "in_progress", "pending_customer", "resolved", "closed"];
const COLUMN_LABELS: Record<string, string> = {
  submitted: "Submitted", assigned: "Assigned", scheduled: "Scheduled",
  in_progress: "In Progress", pending_customer: "Pending Customer", resolved: "Resolved", closed: "Closed",
};

// Mirrors the backend's REQUEST_TRANSITIONS map. This is presentation-only -
// dropping a card always calls the real /status endpoint, which independently
// validates the transition, authorization, and business rules. An invalid
// drop is simply rejected by the server and the board is refreshed.
const ALLOWED_DROP_TARGETS: Record<string, string[]> = {
  submitted: ["assigned", "closed"],
  assigned: ["scheduled", "in_progress"],
  scheduled: ["in_progress"],
  in_progress: ["pending_customer", "resolved"],
  pending_customer: ["in_progress", "resolved"],
  resolved: ["closed"],
  closed: [],
};

export default function KanbanBoardPage() {
  const [board, setBoard] = useState<BoardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const toast = useToast();

  const load = useCallback(() => {
    apiGet<BoardResponse>("/service-requests/board").then(setBoard).catch((e) => setError(e.message));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDrop = async (targetStatus: string, cardId: number, fromStatus: string) => {
    if (fromStatus === targetStatus) return;
    if (!ALLOWED_DROP_TARGETS[fromStatus]?.includes(targetStatus)) {
      toast.error(`Cannot move a request directly from "${fromStatus.replace(/_/g, " ")}" to "${targetStatus.replace(/_/g, " ")}".`);
      return;
    }
    try {
      await changeStatus(cardId, targetStatus);
      toast.success("Request status updated successfully.");
      load();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Unable to update request.");
      load();
    }
  };

  if (error) return <div className="page"><ErrorState message={error} /></div>;
  if (!board) return <div className="page"><LoadingState /></div>;

  return (
    <div className="page">
      <Breadcrumbs items={[{ label: "Dashboard", to: "/dashboard" }, { label: "Kanban Board" }]} />
      {/* <span className="eyebrow">Operations</span> */}
      <h1><span className="page-header-icon"><Kanban size={17} /></span> Request Board</h1>
      <p className="muted" style={{ marginBottom: 18 }}>Drag a card to a new column to change its status. Invalid moves are rejected by the server.</p>

      <div className="kanban-board">
        {COLUMN_ORDER.map((status) => {
          const cards = board.columns[status] || [];
          return (
            <div
              key={status}
              className="kanban-column"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const data = e.dataTransfer.getData("text/plain");
                if (!data) return;
                const [cardId, fromStatus] = data.split("|");
                handleDrop(status, Number(cardId), fromStatus);
              }}
            >
              <div className="kanban-column-header">
                {COLUMN_LABELS[status]} <span className="kanban-count">{cards.length}</span>
              </div>
              <div className="kanban-column-body">
                {cards.map((card) => (
                  <div
                    key={card.id}
                    className="kanban-card"
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData("text/plain", `${card.id}|${status}`);
                    }}
                    onClick={() => navigate(`/requests/${card.id}`)}
                  >
                    <div className="kanban-card-ref">{card.reference_number}</div>
                    {card.customer_name && <div className="kanban-card-customer">{card.customer_name}</div>}
                    <div className="kanban-card-category">{card.category_name}</div>
                    <div className="kanban-card-footer">
                      <PriorityBadge priority={card.priority} />
                      {card.sla_state && (card.sla_state === "breached" || card.sla_state === "at_risk") && (
                        <SlaStateBadge state={card.sla_state as "breached" | "at_risk"} />
                      )}
                    </div>
                    {card.assigned_agent_name && <div className="kanban-card-agent">{card.assigned_agent_name}</div>}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
