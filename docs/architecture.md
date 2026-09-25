# Architecture

## Overview

```
React Frontend (Vite + TypeScript)
        ↓  fetch(), credentials: "include", X-CSRFToken header
Flask REST API
   routes/      → thin HTTP layer: parse request, call services, serialize response
   services/    → business logic (SLA engine, status-transition rules, audit logging)
   security/    → RBAC decorators + object-level authorization checks
   models/      → SQLAlchemy ORM models, one module per domain area
   utils/       → input validation, secure file handling
        ↓  Flask-SQLAlchemy (parameterized queries only)
Relational Database (PostgreSQL in production, SQLite for dev/tests)
```

## Request lifecycle

1. React calls `apiClient.ts`, which attaches the session cookie
   (`credentials: "include"`) and, for state-changing methods, a
   `X-CSRFToken` header fetched once from `/api/auth/csrf-token`.
2. Flask-WTF's `CSRFProtect` validates the token before the view runs.
3. The route function authenticates via `flask_login.current_user`
   (backed by the session cookie) and authorizes via:
   - `@roles_required(...)` — coarse-grained role check.
   - Object-level helpers in `app/security/authz.py` (e.g.
     `can_access_service_request`) — fine-grained ownership/assignment
     check against the specific record being accessed.
4. Input is validated in `app/utils/validation.py` before touching the
   database. Validation errors raise `ValidationError`, caught by a
   global error handler that returns a structured `400` with per-field
   messages — never a stack trace.
5. Business logic lives in `app/services/`:
   - `sla.py` computes response/resolution deadlines from
     `service_categories` / `sla_rules` at request-creation time.
   - `workflow.py` defines the allowed status transitions for both
     service requests and complaints, and generates reference numbers.
   - `audit.py` appends an `AuditLog` row for every state-changing action.
6. The route commits the transaction and serializes the result via each
   model's `to_dict()`, which explicitly lists only the fields safe to
   return (password hashes and internal-only fields are never included).

## Why sessions + CSRF instead of JWT

The spec calls for "one coherent authentication architecture." A
same-site session cookie was chosen over bearer tokens because:

- The frontend and backend are typically deployed under a shared parent
  domain (or a reverse proxy unifies them), making cookie auth simple and
  robust.
- HttpOnly cookies are inherently inaccessible to JavaScript/XSS, which a
  token stored in `localStorage` is not.
- Flask-Login's session handling (idle timeout, `session_protection =
  "strong"`, clean logout/invalidation) is mature and requires no custom
  token-refresh logic.

The trade-off — needing CSRF protection — is handled with a standard
double-submit-style token via Flask-WTF, fetched once and attached
automatically by the frontend's API client.

## Database schema

See [`database.md`](database.md) for the full table reference. The schema
directly follows the original specification's suggested tables, extended
only where necessary (e.g. `service_requests.reference_number`,
`complaints.severity`) per the addition/correction prompt's explicit
clarifications — no unrelated tables were introduced.

## Frontend architecture

- `context/AuthContext.tsx` holds the current user and loading state,
  fetched once from `/api/auth/me` on load.
- `routes/ProtectedRoute.tsx` is a **UX-only** gate: it redirects
  unauthenticated or wrong-role users away from a page, but grants no
  actual access — every real authorization decision happens server-side.
- `services/apiClient.ts` centralizes fetch behavior: JSON
  encoding/decoding, CSRF token attachment, credential inclusion, and
  typed error handling (`ApiError`).
- `services/*.ts` are thin, typed wrappers per resource (requests,
  complaints, users, etc.) so pages never construct raw fetch calls.
- Pages are organized by route, not by role — role-specific UI (e.g. the
  "Assign agent" panel) is conditionally rendered based on
  `useAuth().user.role`, but again, this is presentation only.
