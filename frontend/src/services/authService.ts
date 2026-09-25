import { apiGet, apiPost, apiPatch, resetCsrfToken } from "./apiClient";
import { User } from "../types";

export function login(email: string, password: string, remember?: boolean) {
  return apiPost<{ user: User }>("/auth/login", { email, password, remember: !!remember });
}

export function register(payload: { name: string; email: string; password: string; phone: string; location: string }) {
  return apiPost<{ message: string; email: string }>("/auth/register", payload);
}

export function verifyEmail(email: string, code: string) {
  return apiPost<{ message: string }>("/auth/verify-email", { email, code });
}

export function resendVerification(email: string) {
  return apiPost<{ message: string }>("/auth/resend-verification", { email });
}

export function forgotPassword(email: string) {
  return apiPost<{ message: string }>("/auth/forgot-password", { email });
}

export async function logout() {
  const result = await apiPost<{ message: string }>("/auth/logout");
  resetCsrfToken();
  return result;
}

export function me() {
  return apiGet<{ user: User }>("/auth/me");
}

export function changePassword(current_password: string, new_password: string) {
  return apiPost<{ message: string }>("/auth/change-password", { current_password, new_password });
}

export function updateProfile(payload: { name?: string; phone?: string; location?: string }) {
  return apiPatch<{ user: User }>("/auth/profile", payload);
}
