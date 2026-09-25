import { Role } from "../types";

/**
 * Where a signed-in user should land after login / when they click the
 * brand logo. Customers get a simple, focused "My Requests" list instead
 * of the analytics dashboard - that view is reserved for staff who need
 * cross-request oversight (agents, supervisors, admins).
 */
export function getHomePath(role: Role): string {
  return role === "customer" ? "/requests" : "/dashboard";
}
