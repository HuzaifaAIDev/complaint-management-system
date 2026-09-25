# Security

This document describes the security controls actually implemented in
this codebase (not aspirational ones). File/line references point to
where each control lives.

## Authentication

- Argon2id password hashing (`app/models/user.py`, via `argon2-cffi`),
  with automatic re-hash if parameters ever change (`check_needs_rehash`).
- Passwords are never logged and never returned in any API response
  (`User.to_dict()` deliberately omits `password_hash`).
- Generic "incorrect email or password" message on failed login — the API
  never reveals whether an email is registered.
- Account lockout: 5 failed attempts locks the account for 15 minutes
  (`app/routes/auth.py`).
- **Email verification (OTP-gated signup)**: registering creates the
  account with `email_verified=False`; login is rejected with
  `email_not_verified` until the user submits the code sent to their
  email via `POST /auth/verify-email`. Codes (`app/services/otp.py`) are
  6-digit, generated with `secrets` (CSPRNG), stored only as an Argon2
  hash, expire after `OTP_EXPIRY_MINUTES`, and are rejected after
  `OTP_MAX_ATTEMPTS` — a database read alone can never yield a usable
  code, and repeated guesses are cut off.
- **Forgot password**: `POST /auth/forgot-password` issues a random
  temporary password (meeting the same complexity policy as normal
  passwords) and emails it — never a reset link, and never revealing
  whether the email is registered (identical response either way). The
  account is flagged `must_change_password`, which a global
  `before_request` hook (`app/__init__.py::_register_password_change_enforcement`)
  enforces by rejecting every non-auth API call with
  `403 password_change_required` until the user actually changes the
  password. This is real server-side enforcement, not a frontend-only
  redirect — the restriction cannot be bypassed by calling the API
  directly.
- Session cookies: `HttpOnly` always, `Secure` in production,
  `SameSite=Lax` by default, configurable idle timeout
  (`PERMANENT_SESSION_LIFETIME`), and `session_protection = "strong"` in
  Flask-Login (invalidates the session if the client fingerprint changes).
- Login, registration, OTP verification/resend, and forgot-password are
  all rate-limited via Flask-Limiter.

## Password policy

- Minimum 8 characters, must contain at least one uppercase letter, one
  lowercase letter, one digit, and one special character
  (`app/utils/validation.py::validate_password_strength`). Enforced
  identically at registration, self-service password change, and the
  forced post-temporary-password change.
- Change-password endpoint requires the current password and is rate
  limited.

## RBAC (role-based access control)

Every protected route is decorated with `@roles_required(*roles)`
(`app/security/authz.py`), enforced server-side on every request. The
four roles (`customer`, `agent`, `supervisor`, `admin`) match the
current specification.

## Object-level authorization (IDOR/BOLA)

RBAC alone is not sufficient — a customer with the "customer" role must
still be blocked from another customer's request. `app/security/authz.py`
provides per-resource checks:

- `can_access_service_request` / `can_manage_service_request`
- `can_access_complaint`
- `can_access_message_thread`
- `can_access_invoice`
- `can_access_notification`
- `can_access_document`

Every route that accepts a resource ID (service requests, complaints,
attachments, documents, work orders, invoices, notifications, messages)
calls one of these before returning or mutating data. Tests in
`backend/tests/test_service_requests.py` and
`test_complaints_and_files.py` specifically exercise cross-account access
attempts and confirm they are rejected with `403`.

## Mass assignment protection

Routes only read the specific fields they expect from the request body
(no `**data` blind-passthrough into models). Privileged fields —
`assigned_agent_id`, SLA deadlines, escalation state, internal status,
audit fields, payment status — have no client-writable path; they are
only ever set by server-side logic (e.g. `sla.compute_deadlines`,
the dedicated `/status` and `/assignments` endpoints restricted to
supervisor/admin).

## Google Sign-In

- Standard OAuth 2.0 authorization code flow (`app/services/google_oauth.py`,
  `app/routes/auth.py`), not a client-side "trust the token" pattern —
  the authorization code is exchanged for an identity entirely
  server-side, and the frontend never sees or handles a Google token.
- CSRF-protected via a random `state` value stored server-side in the
  session and compared with `secrets.compare_digest` on callback; a
  missing or mismatched `state` is rejected before any call to Google is
  made.
- Only accounts with a Google-confirmed `email_verified: true` are
  accepted — an unverified Google email is treated as a failure, not a
  login.
- Accounts created via Google are given an unusable random password
  (never disclosed, never emailed) so password-based login can never
  succeed for them; a direct password login attempt on a Google-linked
  account is explicitly rejected with a clear message rather than
  silently failing the password check.
- The button itself is conditionally rendered: the frontend checks
  `GET /auth/google/config` and never shows a "Continue with Google"
  option that would fail because credentials aren't configured.
- All outbound calls to Google's endpoints have a short timeout and are
  wrapped so that any failure (network error, bad response, Google
  downtime) redirects the user back to login with a generic error —
  never a raw exception or stack trace.

## Mandatory-field validation

Service requests cannot be submitted without `category_id`, `description`,
`location`, `priority`, and `preferred_date` — the backend rejects the
request with a `400 validation_error` naming the missing field(s) if any
are absent (`app/routes/service_requests.py::create_request`). Complaints
similarly require `description`, `category`, `severity`, and
`requested_resolution` (`app/routes/complaints.py::create_complaint`).
This is enforced server-side regardless of what the frontend form does.

## Status workflow integrity

`app/models/base.py` defines explicit transition maps
(`REQUEST_TRANSITIONS`, `COMPLAINT_TRANSITIONS`).
`app/services/workflow.py::assert_valid_request_transition` /
`assert_valid_complaint_transition` reject any transition not in the map
with `409 Conflict`. Closing/resolving a complaint without a recorded
resolution is explicitly blocked
(`app/routes/complaints.py::change_complaint_status`).

## File upload security

`app/utils/files.py`:

- Extension allow-list (`ALLOWED_UPLOAD_EXTENSIONS` in `config.py`).
- Best-effort content-type sniffing via `python-magic`, compared against
  the claimed extension (degrades gracefully if `libmagic` isn't
  installed, rather than failing open silently — see code comments).
- Executable file-signature rejection (`MZ`, `ELF` magic bytes) regardless
  of extension.
- Random server-generated filenames (`uuid4().hex`) — the original
  filename is stored only for display, never used as a filesystem path.
- `resolve_safe_path` guarantees the resolved absolute path stays inside
  `UPLOAD_FOLDER`, preventing path traversal even if a stored path were
  ever malformed.
- Every download endpoint re-checks object-level authorization before
  calling `send_file` — there is no public/unauthenticated file URL.
- Global request size cap via `MAX_CONTENT_LENGTH`.

## Database security

- Flask-SQLAlchemy ORM throughout; no raw/string-interpolated SQL
  anywhere in the codebase.
- Foreign keys, unique constraints (email, category+priority SLA rules,
  invoice numbers, reference numbers), and CHECK constraints (roles,
  statuses, priorities, severities, ratings 1–5) enforced at the schema
  level, not just in application code.
- Production config (`config.py::ProductionConfig`) refuses to start with
  a SQLite URL — PostgreSQL is required in production, and the README
  documents creating a dedicated least-privilege database role rather
  than using a superuser.

## Transport & headers

- `_register_security_headers` in `app/__init__.py` sets
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, a restrictive
  `Permissions-Policy`, and a deny-by-default `Content-Security-Policy`
  (`default-src 'none'`) appropriate for a pure JSON API. `Strict-
  Transport-Security` is added automatically whenever a request arrives
  over HTTPS.

## CORS

`Flask-Cors` is configured with an explicit origin allow-list from
`CORS_ORIGINS` (never a wildcard), `supports_credentials=True`, and an
explicit method/header allow-list (`app/__init__.py::_init_extensions`).

## CSRF

Flask-WTF `CSRFProtect` is active globally. The frontend fetches a token
once from `/api/auth/csrf-token` and attaches it as `X-CSRFToken` on every
state-changing request (`frontend/src/services/apiClient.ts`). CSRF is
**not** disabled for the API despite it being consumed by React, per the
original requirement.

## XSS

React escapes all rendered text by default; the codebase contains no use
of `dangerouslySetInnerHTML`. User-generated text (descriptions,
complaints, messages, work notes) is trimmed and length-capped server-side
(`sanitize_text`) but rendering safety is primarily React's automatic
escaping.

## Rate limiting

Flask-Limiter is applied to authentication endpoints (login, register,
change-password) and to request/complaint/attachment/message creation, to
slow down brute-force and abuse without blocking normal usage.

## Secure error handling

The global exception handler in `app/__init__.py` logs unexpected
exceptions server-side and returns a generic
`{"error": "internal_server_error"}` `500` to the client — Python
tracebacks, SQL text, and file paths are never included in a response.

## Secrets management

All secrets (`SECRET_KEY`, `DATABASE_URL`, `MAIL_USERNAME`,
`MAIL_PASSWORD`, etc.) come from environment variables (`backend/.env`,
never committed — see `.gitignore`). `backend/.env.example` documents
every variable with a placeholder value only. `ProductionConfig` fails
fast if `SECRET_KEY` is missing. If `MAIL_SERVER` is left unset, OTP and
temporary-password codes are logged server-side instead of emailed —
convenient for local development, but production deployments must
configure real SMTP credentials or users will never receive their
verification/reset codes.

## Audit logging

`app/services/audit.py::log_action` is called from every state-changing
route and records actor, action, entity type/ID, result, IP address, and
an optional correlation ID (`X-Request-Id`). Passwords, tokens, and
credentials are never logged. The `audit_logs` table has no update/delete
endpoint — it is exposed read-only to admins/supervisors only.
