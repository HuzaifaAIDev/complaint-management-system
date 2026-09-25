import { apiGet, apiPost, apiPatch, apiDelete } from "./apiClient";
import {
  Complaint, Escalation, Paginated, ServiceCategory, SlaRule, User, Customer,
  Notification, Message, DashboardSummary, AuditLogEntry, Invoice, Payment, Feedback,
  TimelineEvent, SlaMonitoringResponse, DashboardCharts, CustomerSummaryResponse,
  AgentWorkload, GlobalSearchResults, AgentCategoryLink, Assignment,
} from "../types";

// --- Complaints ---
export function listComplaints(query?: Record<string, string | number | undefined>) {
  return apiGet<Paginated<Complaint>>("/complaints", query);
}
export function getComplaint(id: number) {
  return apiGet<{ complaint: Complaint; status_history: any[]; escalations: Escalation[] }>(`/complaints/${id}`);
}
export function createComplaint(payload: {
  description: string; category: string; severity: string; requested_resolution: string; contact_number: string; service_request_id?: number;
}) {
  return apiPost<{ complaint: Complaint }>("/complaints", payload);
}
export function changeComplaintStatus(id: number, status: string, resolution?: string) {
  return apiPost<{ complaint: Complaint }>(`/complaints/${id}/status`, { status, resolution });
}

// --- Escalations ---
export function createEscalation(complaintId: number, payload: { escalated_to: number; reason: string; escalation_type?: string }) {
  return apiPost<{ escalation: Escalation }>(`/complaints/${complaintId}/escalations`, payload);
}
export function listEscalations(complaintId: number) {
  return apiGet<{ items: Escalation[] }>(`/complaints/${complaintId}/escalations`);
}
export function resolveEscalation(id: number, resolution_notes?: string) {
  return apiPost<{ escalation: Escalation }>(`/escalations/${id}/resolve`, { resolution_notes });
}

// --- Catalog ---
export function listCategories(activeOnly = true) {
  return apiGet<{ items: ServiceCategory[] }>("/service-categories", { active_only: activeOnly });
}
export function listSlaRules(categoryId?: number) {
  return apiGet<{ items: SlaRule[] }>("/sla-rules", categoryId ? { category_id: categoryId } : undefined);
}

// --- Users / Customers ---
export function listUsers(role?: string) {
  return apiGet<Paginated<User>>("/users", role ? { role } : undefined);
}
// Roles that currently have at least one active staff member, driven by
// whatever the admin has set up - powers the two-step "role, then name"
// assignment flow used by supervisors/admins.
export function listStaffRoles() {
  return apiGet<{ roles: string[] }>("/users/staff-roles");
}
export function myCustomerProfile() {
  return apiGet<{ customer: Customer }>("/customers/me");
}

// --- Agent categories (skills) ---
export function listAgentCategories(agentId: number) {
  return apiGet<{ items: AgentCategoryLink[] }>(`/users/${agentId}/categories`);
}
export function addAgentCategory(agentId: number, categoryId: number) {
  return apiPost<{ item: AgentCategoryLink }>(`/users/${agentId}/categories`, { category_id: categoryId });
}
export function removeAgentCategory(agentId: number, categoryId: number) {
  return apiDelete<{ message: string }>(`/users/${agentId}/categories/${categoryId}`);
}
export function listAgentsForCategory(categoryId: number) {
  return apiGet<{ items: User[] }>(`/service-categories/${categoryId}/agents`);
}

// --- Assignment (category -> agent -> priority -> auto SLA) ---
export function assignComplaint(requestId: number, payload: { category_id: number; agent_id: number; priority: string }) {
  return apiPost<{ assignment: Assignment; service_request: any }>(`/service-requests/${requestId}/assignments`, payload);
}
export function updateAssignment(requestId: number, payload: { category_id?: number; agent_id?: number; priority?: string }) {
  return apiPatch<{ assignment: Assignment; service_request: any }>(`/service-requests/${requestId}/assignments`, payload);
}

// --- Notifications ---
export function listNotifications(unreadOnly = false) {
  return apiGet<Paginated<Notification>>("/notifications", { unread_only: unreadOnly });
}
export function markNotificationRead(id: number) {
  return apiPost<{ notification: Notification }>(`/notifications/${id}/read`);
}
export function markAllNotificationsRead() {
  return apiPost<{ message: string }>("/notifications/read-all");
}

// --- Messages ---
export function listMessages(query?: Record<string, string | number | undefined>) {
  return apiGet<Paginated<Message>>("/messages", query);
}
export function sendMessage(payload: { receiver_id: number; body: string; service_request_id?: number }) {
  return apiPost<{ message_obj: Message }>("/messages", payload);
}

// --- Dashboard ---
export function getDashboardSummary() {
  return apiGet<DashboardSummary>("/dashboard/summary");
}

// --- Audit logs ---
export function listAuditLogs(query?: Record<string, string | number | undefined>) {
  return apiGet<Paginated<AuditLogEntry>>("/audit-logs", query);
}

// --- Invoicing ---
export function listInvoicesForRequest(requestId: number) {
  return apiGet<{ items: Invoice[] }>(`/service-requests/${requestId}/invoices`);
}
export function createInvoice(requestId: number, total_amount: number) {
  return apiPost<{ invoice: Invoice }>(`/service-requests/${requestId}/invoices`, { total_amount });
}
export function recordPayment(invoiceId: number, amount: number, method = "manual", status = "paid") {
  return apiPost<{ payment: Payment }>(`/invoices/${invoiceId}/payments`, { amount, method, status });
}

// --- Timeline ---
export function getRequestTimeline(requestId: number) {
  return apiGet<{ events: TimelineEvent[] }>(`/service-requests/${requestId}/timeline`);
}

// --- SLA monitoring ---
export function getSlaMonitoring() {
  return apiGet<SlaMonitoringResponse>("/dashboard/sla-monitoring");
}

// --- Charts / activity ---
export function getDashboardCharts() {
  return apiGet<DashboardCharts>("/dashboard/charts");
}
export function getRecentActivity(limit = 15) {
  return apiGet<Paginated<AuditLogEntry> & { items: AuditLogEntry[] }>("/dashboard/recent-activity", { limit });
}

// --- Customer 360 ---
export function getCustomerSummary(customerId: number) {
  return apiGet<CustomerSummaryResponse>(`/customers/${customerId}/summary`);
}

// --- Agent workload ---
export function getAgentWorkload() {
  return apiGet<{ items: AgentWorkload[] }>("/users/agents/workload");
}

// --- Global search ---
export function globalSearch(q: string) {
  return apiGet<GlobalSearchResults>("/search", { q });
}

// --- SLA rules (edit/delete) ---
export function updateSlaRule(id: number, payload: { response_hours?: number; resolution_hours?: number }) {
  return apiPatch<{ rule: SlaRule }>(`/sla-rules/${id}`, payload);
}
export function deleteSlaRule(id: number) {
  return apiDelete<{ message: string }>(`/sla-rules/${id}`);
}

// --- Feedback ---
export function submitFeedback(requestId: number, rating: number, comments?: string) {
  return apiPost<{ feedback: Feedback }>(`/feedback/service-requests/${requestId}`, { rating, comments });
}
export function getFeedback(requestId: number) {
  return apiGet<{ feedback: Feedback | null }>(`/feedback/service-requests/${requestId}`);
}
