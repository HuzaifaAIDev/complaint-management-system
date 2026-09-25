export type Role = "customer" | "agent" | "supervisor" | "admin";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  last_login_at?: string | null;
  password_changed_at?: string | null;
  phone?: string | null;
  location?: string | null;
  email_verified?: boolean;
  must_change_password?: boolean;
  auth_provider?: "local" | "google";
  profile_complete?: boolean;
}

export interface Customer {
  id: number;
  user_id: number;
  full_name: string;
  phone: string | null;
  location: string | null;
  profile_complete?: boolean;
  email?: string;
}

export interface AgentCategoryLink {
  id: number;
  agent_id: number;
  category_id: number;
  category_name?: string | null;
}

export interface ServiceCategory {
  id: number;
  name: string;
  description: string | null;
  default_sla_hours: number;
  estimated_duration_minutes: number | null;
  base_price: number | null;
  is_active: boolean;
}

export interface SlaRule {
  id: number;
  category_id: number;
  priority: string;
  response_hours: number;
  resolution_hours: number;
}

export type RequestStatus =
  | "submitted" | "assigned" | "scheduled" | "in_progress"
  | "pending_customer" | "resolved" | "closed" | "reopened";

export type Priority = "low" | "medium" | "high" | "urgent";
export type Severity = "minor" | "moderate" | "major" | "critical";

export interface ServiceRequest {
  id: number;
  reference_number: string;
  customer_id: number;
  category_id: number;
  description: string;
  location: string | null;
  priority: Priority;
  preferred_date: string | null;
  contact_number: string;
  status: RequestStatus;
  sla_response_deadline: string | null;
  sla_resolution_deadline: string | null;
  is_breached: boolean;
  sla_state?: "within_sla" | "at_risk" | "breached" | null;
  remaining_seconds?: number | null;
  created_at: string;
  updated_at: string;
  customer_name?: string | null;
  category_name?: string | null;
  assigned_agent_id?: number | null;
  assigned_agent_name?: string | null;
  assigned_at?: string | null;
}

export interface RequestAttachment {
  id: number;
  service_request_id: number;
  original_filename: string;
  content_type: string | null;
  size_bytes: number | null;
  uploaded_at: string;
}

export interface StatusHistoryEntry {
  id: number;
  old_status: string | null;
  new_status: string;
  changed_by: number | null;
  changed_at: string;
  note?: string | null;
}

export interface Assignment {
  id: number;
  service_request_id: number;
  agent_id: number;
  agent_name: string | null;
  assigned_by: number;
  assigned_at: string;
  active: boolean;
}

export interface Appointment {
  id: number;
  service_request_id: number;
  scheduled_at: string;
  location: string | null;
  status: string;
  assigned_staff_id: number | null;
}

export interface WorkOrder {
  id: number;
  service_request_id: number;
  agent_id: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface WorkNote {
  id: number;
  work_order_id: number;
  note: string;
  added_by: number;
  added_at: string;
}

export type ComplaintStatus = "open" | "in_review" | "escalated" | "resolved" | "closed" | "reopened";

export interface Complaint {
  id: number;
  reference_number: string;
  customer_id: number;
  service_request_id: number | null;
  description: string;
  category: string;
  severity: Severity;
  requested_resolution: string | null;
  contact_number: string;
  status: ComplaintStatus;
  resolution: string | null;
  resolved_at: string | null;
  created_at: string;
  customer_name?: string | null;
}

export interface Escalation {
  id: number;
  complaint_id: number;
  escalation_type: string;
  escalated_by: number;
  escalated_to: number;
  reason: string;
  escalated_at: string;
  resolved_at: string | null;
  resolution_notes: string | null;
}

export interface Message {
  id: number;
  sender_id: number;
  receiver_id: number;
  service_request_id: number | null;
  body: string;
  sent_at: string;
}

export interface Notification {
  id: number;
  user_id: number;
  message: string;
  type: string;
  is_read: boolean;
  created_at: string;
}

export interface Invoice {
  id: number;
  service_request_id: number;
  invoice_no: string;
  total_amount: number;
  amount_paid: number;
  issued_at: string;
}

export interface Payment {
  id: number;
  invoice_id: number;
  amount: number;
  method: string;
  status: string;
  paid_at: string | null;
}

export interface Feedback {
  id: number;
  service_request_id: number;
  rating: number;
  comments: string | null;
  created_at: string;
}

export interface AuditLogEntry {
  id: number;
  user_id: number | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  result: string;
  created_at: string;
}

export interface DashboardSummary {
  scope: Role;
  total_requests: number;
  open_requests: number;
  in_progress_requests: number;
  resolved_requests: number;
  closed_requests: number;
  resolved_today: number;
  total_complaints: number;
  unresolved_complaints: number;
  sla_breaches: number;
  sla_at_risk: number;
  sla_compliance_pct: number | null;
  average_response_hours: number | null;
  average_resolution_hours: number | null;
  average_customer_satisfaction: number | null;
  generated_at: string;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface TimelineEvent {
  type: string;
  label: string;
  status?: string;
  user_id?: number | null;
  note?: string | null;
  at: string;
}

export interface SlaRequestSummary {
  id: number;
  reference_number: string;
  category_name: string | null;
  priority: Priority;
  status: RequestStatus;
  remaining_seconds: number | null;
  sla_resolution_deadline: string | null;
}

export interface SlaMonitoringResponse {
  compliance_pct: number | null;
  breached: SlaRequestSummary[];
  at_risk: SlaRequestSummary[];
  within_sla: SlaRequestSummary[];
  generated_at: string;
}

export interface ChartPoint { key: string; count: number; }
export interface ChartTimePoint { date: string; count: number; }

export interface DashboardCharts {
  requests_by_status: ChartPoint[];
  requests_by_priority: ChartPoint[];
  requests_by_category: ChartPoint[];
  requests_over_time: ChartTimePoint[];
  complaints_by_severity: ChartPoint[];
}

export interface CustomerSummaryResponse {
  customer: Customer;
  summary: {
    total_requests: number;
    open_requests: number;
    resolved_requests: number;
    closed_requests: number;
    total_complaints: number;
    open_complaints: number;
    sla_compliance_pct: number | null;
    average_resolution_hours: number | null;
  };
  requests: {
    id: number; reference_number: string; category_name: string | null;
    priority: Priority; status: RequestStatus; created_at: string; resolved_at: string | null;
  }[];
  complaints: {
    id: number; reference_number: string; category: string;
    severity: Severity; status: ComplaintStatus; resolution: string | null;
  }[];
}

export interface AgentWorkload {
  agent_id: number;
  agent_name: string;
  open: number;
  in_progress: number;
  sla_at_risk: number;
  sla_breached: number;
  completed: number;
  total_assigned: number;
  average_resolution_hours: number | null;
  sla_compliance_pct: number | null;
}

export interface GlobalSearchResults {
  requests: { id: number; reference_number: string; description: string; status: string }[];
  complaints: { id: number; reference_number: string; description: string; status: string }[];
  customers: { id: number; full_name: string; email: string | null }[];
  users: { id: number; name: string; email: string; role: string }[];
}
