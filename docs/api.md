# API Reference

Base URL: `/api` (e.g. `http://localhost:5000/api`).

All responses are JSON. State-changing requests (`POST`/`PUT`/`PATCH`/`DELETE`)
require the `X-CSRFToken` header (see `GET /auth/csrf-token`) and a valid
session cookie, except `POST /auth/register` and `POST /auth/login`
themselves.

Error responses follow `{"error": "<code>", "message": "..."}`, or for
validation failures `{"error": "validation_error", "fields": {"field": "message"}}`.

## Auth (`/auth`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/auth/csrf-token` | none | Returns a CSRF token for subsequent requests. |
| POST | `/auth/register` | none | Registers a new customer account (unverified). Sends an OTP to the given email. Rate limited. |
| POST | `/auth/verify-email` | none | `{"email", "code"}`. Verifies the OTP and activates the account. Rate limited. |
| POST | `/auth/resend-verification` | none | `{"email"}`. Issues a new OTP if the account exists and isn't yet verified. Generic response either way. Rate limited. |
| POST | `/auth/login` | none | Logs in; sets session cookie. Rejects with `email_not_verified` (403) if the account hasn't completed OTP verification. Rate limited. |
| POST | `/auth/forgot-password` | none | `{"email"}`. Issues and emails a temporary password if the account exists; identical generic response either way. Sets `must_change_password`. Rate limited. |
| POST | `/auth/logout` | session | Logs out and clears the session. |
| GET | `/auth/me` | session | Returns the current user (includes `email_verified`, `must_change_password`, `last_login_at`, `password_changed_at`). |
| PATCH | `/auth/profile` | session | Self-service edit of name (and, for customers, phone/address). |
| POST | `/auth/change-password` | session | Changes the current user's password; clears `must_change_password` on success. Rate limited. |
| GET | `/auth/google/config` | none | `{"enabled": bool}` — whether Google Sign-In is configured. Frontend uses this to decide whether to render the button. |
| GET | `/auth/google/login` | none | Redirects to Google's consent screen. `404` if not configured. |
| GET | `/auth/google/callback` | none | Google redirects here with `code`/`state`. Validates the CSRF `state`, exchanges the code, logs in or creates an account, then redirects the browser to `${FRONTEND_URL}/oauth/callback`. Any failure redirects to `${FRONTEND_URL}/login?error=oauth_failed` instead of returning a raw error. |

**`must_change_password` enforcement:** while this flag is set (after a
forgot-password request), every non-auth API endpoint returns
`403 {"error": "password_change_required"}` until `/auth/change-password`
succeeds. This is enforced globally server-side, not just as a frontend
redirect.

## Users (`/users`) — admin/supervisor

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/users` | admin, supervisor | List users (filter by `role`). |
| POST | `/users` | admin | Create a user with any role. |
| GET | `/users/<id>` | admin, supervisor | Get a user. |
| PATCH | `/users/<id>` | admin | Update name/role/active status. |
| POST | `/users/<id>/unlock` | admin | Clear a lockout. |
| GET | `/users/agents/workload` | admin, supervisor | Per-agent workload: open/in-progress/completed counts, SLA at-risk/breached, average resolution time, SLA compliance. |

## Customers (`/customers`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/customers` | admin, supervisor, agent | List customer profiles. |
| GET | `/customers/me` | customer | Own profile. |
| GET | `/customers/<id>` | owner or staff | Get a specific profile (object-level checked). |
| GET | `/customers/<id>/summary` | owner or staff | Customer 360: KPIs plus request/complaint history. Owner-only for customers. |
| PATCH | `/customers/me` | customer | Update own profile. |

## Service categories (`/service-categories`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/service-categories` | any authenticated | List categories (`active_only` query param). |
| POST | `/service-categories` | admin | Create a category. |
| PATCH | `/service-categories/<id>` | admin | Update a category. |

## SLA rules (`/sla-rules`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/sla-rules` | any authenticated | List rules (`category_id` query param). |
| POST | `/sla-rules` | admin | Create a rule (unique per category+priority). |
| PATCH | `/sla-rules/<id>` | admin | Update response/resolution hours. |
| DELETE | `/sla-rules/<id>` | admin | Delete a rule. |

## Service requests (`/service-requests`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/service-requests` | any authenticated | List, scoped to what the caller may see. Supports `search`, `status`, `priority`, `category_id`, `assigned_agent_id`, `customer_id`, `sla_status`, `date_from`, `date_to`, `sort`, `page`, `page_size`. |
| POST | `/service-requests` | customer | Create a request. Requires `category_id`, `description`, `location`, `priority`, `preferred_date` — rejected if any are missing. SLA deadlines computed server-side. |
| GET | `/service-requests/<id>` | owner/assigned/staff | Get one request with customer/category/assigned-agent detail, attachments, and status history. |
| PATCH | `/service-requests/<id>` | owner (pre-assignment) or staff | Edit description/location/priority. |
| POST | `/service-requests/<id>/status` | assigned agent, supervisor, admin | Controlled status transition. |
| POST | `/service-requests/<id>/confirm` | owning customer | `{"action": "confirm"\|"reopen"}`. |
| POST | `/service-requests/<id>/attachments` | owner/assigned/staff | Multipart file upload. |
| GET | `/service-requests/<id>/attachments/<aid>/download` | owner/assigned/staff | Authenticated file download. |
| GET | `/service-requests/<id>/timeline` | owner/assigned/staff | Unified chronological event feed assembled from existing history tables (status changes, assignments, appointments, work orders, linked complaints/escalations, SLA state). |
| GET | `/service-requests/board` | admin, supervisor, agent | Kanban data: requests grouped by status, scoped like the list endpoint. |
| GET | `/service-requests/export` | any authenticated | CSV export honoring the same visibility/filter rules as the list endpoint. |

## Assignments

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/service-requests/<id>/assignments` | supervisor, admin | Assign an agent. Customers/agents can never self-assign. |
| GET | `/service-requests/<id>/assignments` | supervisor, admin, agent | List assignment history. |

## Appointments

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/service-requests/<id>/appointments` | assigned agent, supervisor, admin | Schedule a visit. |
| GET | `/service-requests/<id>/appointments` | owner/assigned/staff | List appointments. |
| PATCH | `/appointments/<id>` | assigned agent, supervisor, admin | Reschedule / change status. |

## Work orders (`/work-orders`)

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/service-requests/<id>/work-orders` | assigned agent, supervisor, admin | Open a work order. |
| GET | `/service-requests/<id>/work-orders` | owner/assigned/staff | List work orders. |
| PATCH | `/work-orders/<id>` | assigned agent, supervisor, admin | Update status/timestamps. |
| POST | `/work-orders/<id>/notes` | assigned agent, supervisor, admin | Add a work note. |
| GET | `/work-orders/<id>/notes` | owner/assigned/staff | List notes. |

## Documents

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/service-requests/<id>/documents` | assigned agent, supervisor, admin | Upload a report/invoice/photo. |
| GET | `/service-requests/<id>/documents` | owner/assigned/staff | List documents. |
| GET | `/documents/<id>/download` | owner/assigned/staff | Authenticated download. |

## Complaints (`/complaints`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/complaints` | any authenticated | List, scoped to caller. Supports `search`, `status`, `severity`, `category`, `customer_id`, `date_from`, `date_to`, `sort`. |
| POST | `/complaints` | customer | File a complaint. Requires `description`, `category`, `severity`, `requested_resolution` — rejected if any are missing. May optionally link to a request. |
| GET | `/complaints/<id>` | owner/assigned/staff | Get one complaint with history + escalations. |
| POST | `/complaints/<id>/status` | supervisor, admin | Controlled transition; blocks resolve/close without a resolution. |
| POST | `/complaints/<id>/reopen` | owning customer | Reopen a resolved/closed complaint. |
| GET | `/complaints/export` | any authenticated | CSV export honoring the same visibility/filter rules as the list endpoint. |

## Escalations

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/complaints/<id>/escalations` | agent, supervisor, admin | Escalate to a supervisor/admin. |
| GET | `/complaints/<id>/escalations` | owner/assigned/staff | List escalations. |
| POST | `/escalations/<id>/resolve` | supervisor (own), admin | Mark an escalation resolved. |

## Messages (`/messages`)

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/messages` | any authenticated | Send a message; customers can't message other customers. |
| GET | `/messages` | any authenticated | List own conversations (`with_user_id`, `service_request_id` filters). |

## Notifications (`/notifications`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/notifications` | any authenticated | List own notifications (`unread_only`). |
| POST | `/notifications/<id>/read` | owner | Mark one read. |
| POST | `/notifications/read-all` | any authenticated | Mark all own notifications read. |

## Invoicing

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/service-requests/<id>/invoices` | admin | Create an invoice. |
| GET | `/service-requests/<id>/invoices` | owner/staff | List invoices for a request. |
| GET | `/invoices/<id>` | owner/staff | Get one invoice with payments. |
| POST | `/invoices/<id>/payments` | admin | Record a payment. |

## Feedback (`/feedback`)

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/feedback/service-requests/<id>` | owning customer | Submit rating (1–5) after resolution/closure. |
| GET | `/feedback/service-requests/<id>` | owner/assigned/staff | Get feedback for a request. |

## Audit logs (`/audit-logs`) — read-only

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/audit-logs` | admin, supervisor | List entries (`entity_type`, `user_id` filters). |

## Dashboard (`/dashboard`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/dashboard/summary` | any authenticated | Role-scoped KPIs: requests by status, SLA breaches/at-risk, complaint counts, response/resolution times, satisfaction. |
| GET | `/dashboard/charts` | any authenticated | Chart-ready aggregates: requests over time/by status/by priority/by category, complaints by severity. |
| GET | `/dashboard/recent-activity` | any authenticated | Recent audit-log activity feed. Customers/agents see only their own actions; admin/supervisor see the full operational feed. |
| GET | `/dashboard/sla-monitoring` | admin, supervisor, agent | SLA Monitoring Center: breached / at-risk / within-SLA buckets with compliance percentage. Not exposed to customers. |

## Search (`/search`)

| Method | Path | Role | Description |
|---|---|---|---|
| GET | `/search?q=` | any authenticated | Server-side, role-scoped search across requests, complaints, customers, and users. Customer/user groups are staff-only. Never returns more than a handful of results per group. |

## Pagination

List endpoints accept `page` (default 1) and `page_size` (default 20, max
100) and return `{"items": [...], "page": N, "page_size": N, "total": N}`.
