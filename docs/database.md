# Database

## Engine

- **Development / tests**: SQLite (zero setup — `DATABASE_URL=sqlite:///dev.db`).
- **Production**: PostgreSQL, required by `ProductionConfig` (the app
  refuses to start with a SQLite URL when `FLASK_ENV=production`).

## Migrations

Schema changes are managed with Flask-Migrate/Alembic
(`backend/migrations/`). Four migrations exist: the initial schema
(all core tables), a follow-up adding `last_login_at` and
`password_changed_at` to `users`, a follow-up adding the OTP table and
email-verification/forced-password-change columns, and a follow-up
adding `auth_provider`/`google_id` for Google Sign-In. To make a further
schema change:

```bash
# after editing a model in app/models/
flask db migrate -m "describe the change"
flask db upgrade
```

Never drop and recreate the database to apply a schema change — always go
through a migration so existing data is preserved.

## Tables

This follows the original specification's suggested relational model,
extended only where the addition/correction prompt explicitly required it
(reference numbers, complaint category/severity/requested-resolution,
timestamps, escalation typing). No unrelated tables were introduced.

| Table | Key columns | Notes |
|---|---|---|
| `users` | id, name, email (unique), password_hash, role, is_active, failed_login_count, locked_until, last_login_at, password_changed_at, email_verified, must_change_password, auth_provider, google_id (unique) | Argon2id hash; role has a CHECK constraint. `email_verified` gates login; `must_change_password` is set by the forgot-password flow and enforced server-side on every request until cleared. `auth_provider` is `local` or `google`; Google-linked accounts have an unusable random password and can never log in with one. |
| `email_otps` | id, user_id (FK), purpose, code_hash, attempts, max_attempts, expires_at, used_at, created_at | One-time codes for signup verification and password reset. The code is stored only as an Argon2 hash — never in plaintext. Purpose has a CHECK constraint (`signup_verification`, `password_reset`). |
| `customers` | id, user_id (FK, unique), full_name, phone, address | One-to-one with `users`. |
| `service_categories` | id, name (unique), default_sla_hours, estimated_duration_minutes, base_price, is_active | |
| `sla_rules` | id, category_id (FK), priority, response_hours, resolution_hours | Unique on (category_id, priority). |
| `service_requests` | id, reference_number (unique), customer_id (FK), category_id (FK), description, location, priority, preferred_date, status, sla_response_deadline, sla_resolution_deadline, responded_at, resolved_at, created_by, updated_by | Status has a CHECK constraint; deadlines are server-computed only. |
| `request_attachments` | id, service_request_id (FK), file_path, original_filename, content_type, size_bytes, uploaded_by, uploaded_at | `file_path` is a server-generated random name, never client input. |
| `request_status_history` | id, service_request_id (FK), old_status, new_status, changed_by (FK), changed_at, note | Append-only audit trail. |
| `assignments` | id, service_request_id (FK), agent_id (FK), assigned_by (FK), assigned_at, active | Only one active assignment per request at a time. |
| `appointments` | id, service_request_id (FK), scheduled_at, location, status, assigned_staff_id (FK) | |
| `work_orders` | id, service_request_id (FK), agent_id (FK), status, started_at, completed_at | |
| `work_notes` | id, work_order_id (FK), note, added_by (FK), added_at | |
| `request_documents` | id, service_request_id (FK), file_path, original_filename, doc_type, uploaded_by, uploaded_at | Reports/invoices/photos generated for a request. |
| `complaints` | id, reference_number (unique), customer_id (FK), service_request_id (FK, nullable), description, category, severity, requested_resolution, status, resolution, resolved_at | May be standalone or tied to a request, per spec. |
| `complaint_status_history` | id, complaint_id (FK), old_status, new_status, changed_by (FK), changed_at | Append-only. |
| `escalations` | id, complaint_id (FK), escalation_type, escalated_by (FK), escalated_to (FK), reason, escalated_at, resolved_at, resolution_notes | `escalated_to` is restricted to supervisor/admin users at the application layer. |
| `messages` | id, sender_id (FK), receiver_id (FK), service_request_id (FK, nullable), body, sent_at | |
| `notifications` | id, user_id (FK), message, type, is_read, created_at | |
| `invoices` | id, service_request_id (FK), invoice_no (unique), total_amount, issued_at, issued_by (FK) | |
| `payments` | id, invoice_id (FK), amount, method, status, paid_at, recorded_by (FK) | Status has a CHECK constraint. |
| `feedback` | id, service_request_id (FK, unique), rating (1–5, CHECK), comments, created_at | One feedback record per request. |
| `audit_logs` | id, user_id (FK, nullable), action, entity_type, entity_id, result, ip_address, request_id, details, created_at | Read-only via the API; no update/delete endpoint exists. |

## Constraints used throughout

- **Foreign keys** on every relationship listed above.
- **Unique constraints**: `users.email`, `service_requests.reference_number`,
  `complaints.reference_number`, `invoices.invoice_no`,
  `service_categories.name`, `(sla_rules.category_id, sla_rules.priority)`,
  `feedback.service_request_id`.
- **CHECK constraints**: `users.role`, `service_requests.status`/`priority`,
  `sla_rules.priority`, `complaints.status`/`severity`,
  `escalations.escalation_type`, `work_orders.status`,
  `payments.status`, `feedback.rating BETWEEN 1 AND 5`.
- **Timestamps**: `created_at`/`updated_at` are present wherever the data
  is mutable and the history matters; append-only history tables
  (`*_status_history`, `work_notes`, `messages`, `audit_logs`) use a
  single `changed_at`/`added_at`/`sent_at`/`created_at` instead, since
  they are never updated after creation.
