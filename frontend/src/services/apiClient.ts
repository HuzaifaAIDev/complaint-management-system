const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

let csrfToken: string | null = null;

export class ApiError extends Error {
  status: number;
  fields?: Record<string, string>;
  code?: string;

  constructor(message: string, status: number, fields?: Record<string, string>, code?: string) {
    super(message);
    this.status = status;
    this.fields = fields;
    this.code = code;
  }
}

async function ensureCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;
  const res = await fetch(`${API_BASE_URL}/auth/csrf-token`, { credentials: "include" });
  const data = await res.json();
  csrfToken = data.csrf_token;
  return csrfToken as string;
}

export function resetCsrfToken() {
  csrfToken = null;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  isFormData?: boolean;
  query?: Record<string, string | number | boolean | undefined>;
}

function buildQuery(query?: RequestOptions["query"]): string {
  if (!query) return "";
  const params = new URLSearchParams();
  Object.entries(query).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method || "GET";
  const needsCsrf = ["POST", "PUT", "PATCH", "DELETE"].includes(method);

  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;

  if (options.isFormData) {
    body = options.body as FormData;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  if (needsCsrf) {
    headers["X-CSRFToken"] = await ensureCsrfToken();
  }

  const res = await fetch(`${API_BASE_URL}${path}${buildQuery(options.query)}`, {
    method,
    headers,
    body,
    credentials: "include",
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await res.json() : null;

  if (!res.ok) {
    if (res.status === 400 && data?.fields) {
      throw new ApiError(data.message || "Validation failed", res.status, data.fields, data?.error);
    }
    throw new ApiError(data?.message || data?.error || `Request failed (${res.status})`, res.status, undefined, data?.error);
  }

  return data as T;
}

export function apiGet<T>(path: string, query?: RequestOptions["query"]) {
  return apiRequest<T>(path, { method: "GET", query });
}

export function apiPost<T>(path: string, body?: unknown) {
  return apiRequest<T>(path, { method: "POST", body });
}

export function apiPatch<T>(path: string, body?: unknown) {
  return apiRequest<T>(path, { method: "PATCH", body });
}

export function apiDelete<T>(path: string) {
  return apiRequest<T>(path, { method: "DELETE" });
}

export function apiUpload<T>(path: string, formData: FormData) {
  return apiRequest<T>(path, { method: "POST", body: formData, isFormData: true });
}

export function fileDownloadUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export { API_BASE_URL };
