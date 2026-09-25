import { apiGet, apiPatch, apiPost, apiUpload, fileDownloadUrl } from "./apiClient";
import {
  ServiceRequest, RequestAttachment, StatusHistoryEntry, Assignment,
  Appointment, WorkOrder, WorkNote, Paginated,
} from "../types";

export function listRequests(query?: Record<string, string | number | undefined>) {
  return apiGet<Paginated<ServiceRequest>>("/service-requests", query);
}

export function getRequest(id: number) {
  return apiGet<{ service_request: ServiceRequest; attachments: RequestAttachment[]; status_history: StatusHistoryEntry[] }>(
    `/service-requests/${id}`
  );
}

export function createRequest(payload: {
  category_id: number; description: string; location: string; priority: string; preferred_date: string; contact_number: string;
}) {
  return apiPost<{ service_request: ServiceRequest }>("/service-requests", payload);
}

export function updateRequest(id: number, payload: Partial<{ description: string; location: string; priority: string }>) {
  return apiPatch<{ service_request: ServiceRequest }>(`/service-requests/${id}`, payload);
}

export function changeStatus(id: number, status: string, note?: string) {
  return apiPost<{ service_request: ServiceRequest }>(`/service-requests/${id}/status`, { status, note });
}

export function confirmResolution(id: number, note?: string) {
  return apiPost<{ service_request: ServiceRequest }>(`/service-requests/${id}/confirm`, { action: "confirm", note });
}

export function uploadAttachment(id: number, file: File) {
  const fd = new FormData();
  fd.append("file", file);
  return apiUpload<{ attachment: RequestAttachment }>(`/service-requests/${id}/attachments`, fd);
}

export function attachmentDownloadUrl(requestId: number, attachmentId: number) {
  return fileDownloadUrl(`/service-requests/${requestId}/attachments/${attachmentId}/download`);
}

export function assignComplaint(requestId: number, payload: { category_id: number; agent_id: number; priority: string }) {
  return apiPost<{ assignment: Assignment; service_request: ServiceRequest }>(`/service-requests/${requestId}/assignments`, payload);
}

export function updateAssignment(requestId: number, payload: Partial<{ category_id: number; agent_id: number; priority: string }>) {
  return apiPatch<{ assignment: Assignment; service_request: ServiceRequest }>(`/service-requests/${requestId}/assignments`, payload);
}

export function listAssignments(requestId: number) {
  return apiGet<{ items: Assignment[] }>(`/service-requests/${requestId}/assignments`);
}

export function createAppointment(requestId: number, payload: { scheduled_at: string; location?: string }) {
  return apiPost<{ appointment: Appointment }>(`/service-requests/${requestId}/appointments`, payload);
}

export function listAppointments(requestId: number) {
  return apiGet<{ items: Appointment[] }>(`/service-requests/${requestId}/appointments`);
}

export function createWorkOrder(requestId: number, agentId?: number) {
  return apiPost<{ work_order: WorkOrder }>(`/service-requests/${requestId}/work-orders`, agentId ? { agent_id: agentId } : {});
}

export function listWorkOrders(requestId: number) {
  return apiGet<{ items: WorkOrder[] }>(`/service-requests/${requestId}/work-orders`);
}

export function updateWorkOrder(id: number, status: string) {
  return apiPatch<{ work_order: WorkOrder }>(`/work-orders/${id}`, { status });
}

export function addWorkNote(workOrderId: number, note: string) {
  return apiPost<{ note: WorkNote }>(`/work-orders/${workOrderId}/notes`, { note });
}

export function listWorkNotes(workOrderId: number) {
  return apiGet<{ items: WorkNote[] }>(`/work-orders/${workOrderId}/notes`);
}
