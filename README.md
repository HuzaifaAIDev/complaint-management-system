# Professional Service Request & Complaint Management System

A full-stack platform for organizations that provide professional services
and need a structured way to receive service requests, assign staff, track
work, collect documents, handle complaints, and measure service performance.

React (TypeScript) frontend + Flask REST API backend, with role-based and
object-level authorization enforced entirely on the server.

## Contents

- [Architecture](#architecture)
- [Features](#features)
- [User Roles](#user-roles)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Backend Setup](#backend-setup)
- [Frontend Setup](#frontend-setup)
- [Database Setup](#database-setup)
- [Environment Variables](#environment-variables)
- [API Documentation](#api-documentation)
- [Security](#security)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Architecture

```
React Frontend (Vite + TypeScript)
        ↓  fetch, credentials: "include"
Flask REST API  (routes → services → models)
        ↓  Flask-SQLAlchemy (parameterized ORM)
Relational Database  (PostgreSQL in production; SQLite for local/dev/tests)
```

- **Authentication**: session cookie (HttpOnly, SameSite, Secure in
  production) issued by Flask-Login on `/api/auth/login`. The React app
  never stores a token; the browser sends the cookie automatically.
- **CSRF**: Flask-WTF `CSRFProtect` validates an `X-CSRFToken` header on
  every state-changing request. The frontend fetches the token once from
  `/api/auth/csrf-token` and attaches it automatically (see
  `frontend/src/services/apiClient.ts`).
- **Authorization**: two independent layers, both server-side only.
  1. **RBAC** — `@roles_required(...)` decorators gate entire endpoints by
     role (`app/security/authz.py`).
  2. **Object-level** — `can_access_service_request`, `can_access_complaint`,
     etc. check the actual relationship between the logged-in user and the
     specific record before returning or mutating it. Knowing an ID is
     never sufficient on its own.
  React route guards (`ProtectedRoute.tsx`) exist purely for UX/navigation;
  they grant no access on their own.
- **File handling**: uploads are validated (extension allow-list, content
  sniffing, executable-signature rejection), stored under a
  server-generated random filename, and served only through an
  authenticated, authorization-checked download endpoint. The original
  filename is stored for display but never used as a filesystem path.
- **Audit logging**: `app/services/audit.py` records actor, action, entity,
  result, and timestamp for every state-changing operation into the
  `audit_logs` table, which is exposed only via a read-only endpoint.

## Features

- Service request lifecycle: submission → validation → assignment →
  scheduling → work execution → SLA monitoring → resolution → customer
  confirmation → closure/feedback, with a server-enforced status state
  machine (including customer-initiated reopening). Submission requires
  category, description, location, priority, and preferred date — the
  backend rejects incomplete requests outright.
- OTP-gated signup: registering creates an unverified account, emails a
  one-time verification code, and blocks login until the code is
  confirmed. Codes are hashed, expire, and are attempt-limited.
- Forgot password: issues a temporary password by email (never a
  plaintext-in-URL reset link) and forces the user to set a new password
  before any other action succeeds — enforced server-side on every
  request, not just as a frontend redirect.
- Strong password policy (8+ characters, upper/lower/digit/special
  character) enforced identically at signup, password change, and
  forced password reset.
- SLA engine: response/resolution deadlines computed server-side from
  category + priority at creation time; breach and at-risk detection.
- Complaint workflow with mandatory category, severity, and requested
  resolution, and a status state machine that blocks closing/resolving
  without a recorded resolution.
- Escalation tracking (type, escalated-by/to, reason, resolution).
- Assignment (supervisor/admin only — customers can never self-assign),
  appointments/scheduling, work orders and work notes.
- Secure file attachments and generated documents (reports/invoices/photos),
  with inline preview for images.
- Internal messaging scoped to participants only, and per-user
  notifications with an unread-count bell in the navigation.
- Optional invoicing module: invoices and payments, restricted to
  admin/the owning customer.
- Customer feedback/rating after resolution.
- Role-scoped enterprise dashboard: KPIs, charts (requests over time, by
  status, by priority, by category), recent activity, tailored per role
  (customers see only their own data).
- SLA Monitoring Center: breached / at-risk / within-SLA buckets with
  live countdowns.
- Customer 360 view, agent workload view (supervisor/admin).
- Kanban board with drag-and-drop status changes — every drop is
  re-validated server-side against the real workflow rules.
- Global search across requests, complaints, customers, and users —
  server-side, role-scoped, debounced.
- Advanced filtering, sorting, and pagination on all list views, plus
  CSV export (scoped to the same authorization/filter rules as the list).
- Command palette (Ctrl/Cmd+K), breadcrumbs, toast notifications,
  confirmation dialogs, and light/dark/system theme.
- Read-only audit log viewer for admins/supervisors.

## User Roles

| Role | Can | Cannot |
|---|---|---|
| **Customer** | Create/view own requests & complaints, upload attachments, message assigned staff, confirm/reopen resolutions, submit feedback | Assign staff, change internal status directly, see other customers' records |
| **Service Agent / Technician** | View/work assigned requests, log work orders/notes, upload evidence, update status on assigned work | Assign requests, access requests they're not assigned to |
| **Supervisor** | Assign staff, manage SLA/status transitions, resolve escalations, view all requests/complaints, manage users (limited) | Modify audit logs, delete business records |
| **Administrator** | Full access: users, service catalog, SLA rules, all requests/complaints, audit logs, invoices/payments | — |

## Project Structure

```
.
├── backend/                 Flask REST API
│   ├── app/
│   │   ├── routes/          One blueprint per resource
│   │   ├── models/          SQLAlchemy models (grouped by domain)
│   │   ├── services/        SLA engine, workflow/status rules, audit logging
│   │   ├── security/        RBAC + object-level authorization
│   │   └── utils/           File handling, input validation
│   ├── migrations/          Flask-Migrate/Alembic migrations
│   ├── tests/                Pytest suite (auth, RBAC, IDOR, workflow, files)
│   ├── config.py
│   ├── run.py
│   ├── seed.py               Local/demo seed data
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 React + TypeScript + Vite
│   └── src/
│       ├── pages/            Route-level views
│       ├── components/       Shared UI
│       ├── layouts/          App shell/navigation
│       ├── routes/           Route guards
│       ├── context/          Auth state
│       ├── services/         API client + per-resource calls
│       └── types/            Shared TypeScript types
├── docs/                     architecture.md, security.md, api.md, database.md, deployment.md
└── .gitignore
```

## Requirements

- Python 3.11+
- Node.js 20+ and npm 10+
- PostgreSQL 14+ (production) — SQLite works out of the box for local
  development and the test suite, no separate install needed
- (optional) `libmagic` system library for stronger file-content sniffing
  in `app/utils/files.py` — the app degrades gracefully without it

## Installation

Clone the repository, then set up the backend and frontend as described
below. The two run as independent processes during development.

## Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set SECRET_KEY, DATABASE_URL, CORS_ORIGINS, etc.

export FLASK_APP=run.py          # Windows (cmd): set FLASK_APP=run.py
flask db upgrade                  # creates all tables via migrations

python seed.py                    # optional: creates one demo user per role

flask run                         # or: python run.py
# API now listening on http://127.0.0.1:5000
```

## Frontend Setup

```bash
cd frontend
npm install

cp .env.example .env
# edit .env if your API isn't on the default http://localhost:5000/api

npm run dev
# App now listening on http://localhost:5173

npm run build                     # production build → frontend/dist
```

## Database Setup

- **Local/dev/tests**: the default `DATABASE_URL=sqlite:///dev.db` in
  `.env.example` needs no setup at all.
- **Production**: use PostgreSQL.
  ```bash
  createdb servicecomplaint
  createuser svc_app_user --pwprompt          # least-privilege app account
  ```
  Set `DATABASE_URL=postgresql+psycopg2://svc_app_user:<password>@<host>:5432/servicecomplaint`
  in your production environment (never in a committed file), then run
  `flask db upgrade`.
- Schema changes are always made via `flask db migrate -m "..."` followed
  by `flask db upgrade` — never by dropping/recreating the database.

## Email/OTP Setup

Signup verification and password reset both send a one-time code by
email. This requires SMTP credentials in `backend/.env`:

```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=1
MAIL_USERNAME=your-account@gmail.com
MAIL_PASSWORD=your-app-password   # use an app password, not your real account password
MAIL_DEFAULT_SENDER=your-account@gmail.com
```

Any standard SMTP provider works (Gmail with an App Password, SendGrid,
Mailgun, Postmark, your own mail server, etc.) — just point `MAIL_SERVER`
at it.

**Local development without real email:** if `MAIL_SERVER` is left
blank, the app does not fail — it logs the OTP/temporary-password code to
the backend console instead (`flask run` output) so you can complete the
signup/reset flow without configuring a mailbox. This must not be relied
on in any real deployment; production requires `MAIL_SERVER` to be set.

## Google Sign-In Setup

"Continue with Google" is a standard OAuth 2.0 authorization-code flow —
no third-party SDK, three plain HTTPS calls
(`app/services/google_oauth.py`). It's entirely optional: the frontend
calls `GET /api/auth/google/config` on load and only renders the button
when the backend reports it's configured.

To enable it:

1. In the [Google Cloud Console](https://console.cloud.google.com/apis/credentials),
   create an **OAuth client ID** of type **Web application**.
2. Add an Authorized redirect URI matching `GOOGLE_REDIRECT_URI` exactly,
   e.g. `http://localhost:5000/api/auth/google/callback` for local dev.
3. Set in `backend/.env`:
   ```bash
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
   FRONTEND_URL=http://localhost:5173
   ```

How it works: clicking the button navigates the browser (not a fetch) to
`/api/auth/google/login`, which redirects to Google's consent screen with
a random CSRF `state` stored in the session. Google redirects back to
`/api/auth/google/callback`, which validates `state`, exchanges the code
for an identity, and either logs in an existing account (matched by
verified email) or creates a new customer account — then redirects the
browser to `${FRONTEND_URL}/oauth/callback`, which refreshes the
frontend's session state and routes to the dashboard. Accounts created
this way have `auth_provider = "google"` and can never log in with a
password (the password field is set to an unusable random value).

## Environment Variables

### Backend (`backend/.env`, see `backend/.env.example`)

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session/CSRF signing key. Required in production. |
| `DATABASE_URL` | SQLAlchemy connection string. |
| `MAIL_SERVER` | SMTP server for OTP/reset emails. If unset, codes are logged server-side instead of emailed, so local dev works without real credentials — see [Email/OTP setup](#emailotp-setup). |
| `MAIL_PORT` | SMTP port (587 for TLS, 465 for SSL). |
| `MAIL_USE_TLS` / `MAIL_USE_SSL` | Transport security — use exactly one, not both. |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | SMTP credentials. Never commit real values. |
| `MAIL_DEFAULT_SENDER` | From-address for outgoing email. |
| `OTP_EXPIRY_MINUTES` | How long a verification/reset code stays valid (default 10). |
| `OTP_MAX_ATTEMPTS` | Attempts allowed per code before it's rejected (default 5). |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth 2.0 credentials for "Continue with Google". Leave blank to disable — the button hides itself automatically when unset. |
| `GOOGLE_REDIRECT_URI` | Must exactly match an Authorized redirect URI configured on the Google OAuth client (e.g. `http://localhost:5000/api/auth/google/callback`). |
| `FRONTEND_URL` | Where the backend sends the browser after a Google login completes (e.g. `http://localhost:5173`). |
| `CORS_ORIGINS` | Comma-separated list of trusted frontend origins. |
| `SESSION_COOKIE_SECURE` | `1` in production (HTTPS only). |
| `SESSION_COOKIE_SAMESITE` | Cookie SameSite policy (default `Lax`). |
| `PERMANENT_SESSION_LIFETIME_MINUTES` | Session idle timeout. |
| `UPLOAD_FOLDER` | Where uploaded files are stored on disk. |
| `MAX_CONTENT_LENGTH_MB` | Max request/upload size. |
| `RATELIMIT_STORAGE_URI` | `memory://` for dev, `redis://...` for production. |
| `DEFAULT_RESPONSE_HOURS` / `DEFAULT_RESOLUTION_HOURS` | SLA fallback when no explicit rule exists. |
| `REQUEST_REF_PREFIX` | Prefix for generated request reference numbers. |

### Frontend (`frontend/.env`, see `frontend/.env.example`)

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Base URL of the Flask API. Never put secrets here — anything bundled into a Vite build is visible to end users. |

## API Documentation

See [`docs/api.md`](docs/api.md) for the full endpoint reference
(method, path, auth/role requirements, request/response shape).

## Security

See [`docs/security.md`](docs/security.md) for the full write-up. Summary:
OTP-gated email verification at signup, Argon2id password hashing with a
strong complexity policy (8+ chars, upper/lower/digit/special) and account
lockout, forgot-password via a one-time emailed temporary password that
forces a password change (enforced server-side on every request, not just
in the UI), session-cookie auth with CSRF protection, server-enforced
RBAC + object-level authorization on every resource, mass-assignment
protection (privileged fields are never accepted from client input),
mandatory-field validation on requests/complaints so nothing incomplete
can be submitted, validated/sandboxed file uploads with path-traversal
protection, parameterized ORM queries, restrictive CORS, production
security headers, rate limiting on sensitive endpoints, and audit logging
that never records secrets or OTP codes.

## Testing

```bash
cd backend
source .venv/bin/activate
pytest                # full suite
pytest -v              # verbose
```

The suite covers: OTP-gated registration and email verification (including
wrong-code rejection), forgot-password issuing a temporary password that
invalidates the old one, server-side enforcement blocking every endpoint
until a temporary password is changed, account lockout, generic auth
error messages, password exposure checks, mandatory-field validation on
requests/complaints, SLA deadline computation and tamper-resistance,
IDOR/BOLA (cross-customer/cross-role access attempts), invalid status
transitions, mass-assignment protection, complaint
resolution-before-closing enforcement, role-scoped dashboards, SLA
monitoring access control, Customer 360
ownership checks, agent workload admin-only access, global search
scoping, CSV export scoping, disallowed file types, and cross-account
attachment access.

## Deployment

See [`docs/deployment.md`](docs/deployment.md) for full instructions.
Summary: run the backend with a production WSGI server (`gunicorn`), the
frontend as a static build served by a CDN/static host or reverse proxy,
PostgreSQL as the database, HTTPS everywhere with HSTS enabled, and all
secrets supplied via environment variables — never committed.

## Troubleshooting

| Problem | Likely cause / fix |
|---|---|
| `RuntimeError: SECRET_KEY must be set in production` | Set `SECRET_KEY` in the production environment. |
| Frontend requests fail with CORS errors | Confirm `CORS_ORIGINS` in backend `.env` includes your frontend's exact origin. |
| `401` on every request from the frontend | Cookie not being sent — confirm the frontend is calling the correct `VITE_API_BASE_URL` and that `credentials: "include"` isn't blocked by a mismatched CORS origin. |
| `400 validation_error` on login/register | Check the `fields` object in the JSON response for the specific field message. |
| Registered but can't log in | Check the backend console log for the OTP code (if `MAIL_SERVER` isn't configured) or your inbox, then verify via `/verify-email`. Login is blocked until the email is verified. |
| Forgot-password email never arrives | Confirm `MAIL_SERVER`/`MAIL_USERNAME`/`MAIL_PASSWORD` are set correctly; without them the temporary password is logged to the backend console instead. |
| Stuck on "set a new password" screen | This means `must_change_password` is set on the account (e.g. after a forgot-password request) — the backend blocks every other endpoint until a new password is submitted there. |
| `403 password_change_required` from the API | Same as above — call `/api/auth/change-password` first. |
| "Continue with Google" button doesn't appear | `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/`GOOGLE_REDIRECT_URI` aren't all set in `backend/.env` — the button only renders when the backend reports it's configured. |
| Google login redirects back with `?error=oauth_failed` | Usually a redirect URI mismatch — confirm `GOOGLE_REDIRECT_URI` matches an Authorized redirect URI on the Google OAuth client exactly, including scheme and port. |
| File upload rejected | Extension not in the allow-list, or content sniffing detected a mismatch. See `ALLOWED_UPLOAD_EXTENSIONS` in `config.py`. |
| `flask db upgrade` fails on a fresh clone | Ensure `DATABASE_URL` is set and the target database/user exists before running migrations. |

## License

No specific license has been requested for this project. Add a `LICENSE`
file with the license of your choice before publishing the repository
publicly (e.g. MIT, Apache-2.0), or keep it private if it's for
coursework submission only.
