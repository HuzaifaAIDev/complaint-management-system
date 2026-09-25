# Deployment

This describes a straightforward production deployment: Flask served by
Gunicorn behind a reverse proxy (nginx or a managed load balancer),
PostgreSQL as the database, and the React build served as static files
(from the same reverse proxy, a static host, or a CDN).

## 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Environment (set via your process manager / platform secrets, not a file
# committed to the repo):
export FLASK_ENV=production
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export DATABASE_URL="postgresql+psycopg2://svc_app_user:<password>@<host>:5432/servicecomplaint"
export CORS_ORIGINS="https://your-frontend-domain.com"
export SESSION_COOKIE_SECURE=1
export RATELIMIT_STORAGE_URI="redis://<redis-host>:6379/0"

flask db upgrade

gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

Notes:

- `ProductionConfig` (in `config.py`) refuses to start without a
  `SECRET_KEY`, and refuses a SQLite `DATABASE_URL` — PostgreSQL is
  required in production.
- Use a **dedicated least-privilege database role** (`svc_app_user` above),
  not a superuser. Grant it only the privileges it needs on the
  `servicecomplaint` database.
- Put Gunicorn behind a reverse proxy (nginx, Caddy, or your platform's
  load balancer) that terminates TLS. Flask's own `SESSION_COOKIE_SECURE`
  requires the connection reaching Flask to be over HTTPS (or the proxy
  to set `X-Forwarded-Proto` correctly if Flask is behind TLS
  termination).
- For horizontal scaling, move `RATELIMIT_STORAGE_URI` to Redis (shown
  above) so rate limits are shared across workers/instances instead of
  per-process memory.
- `UPLOAD_FOLDER` should point at persistent storage (a mounted volume or
  equivalent) — it is not committed to the repo and does not survive a
  container rebuild otherwise.

## 2. Frontend

```bash
cd frontend
npm install
echo "VITE_API_BASE_URL=https://api.your-domain.com/api" > .env
npm run build
# → static output in frontend/dist/, deploy to any static host/CDN
# (nginx, Netlify, Vercel static hosting, S3+CloudFront, etc.)
```

Because this is a client-side routed SPA, configure your static host to
fall back to `index.html` for unknown paths (so refreshing e.g.
`/requests/42` doesn't 404).

## 3. Database

```bash
# One-time provisioning
createdb servicecomplaint
createuser svc_app_user --pwprompt
psql -c "GRANT ALL PRIVILEGES ON DATABASE servicecomplaint TO svc_app_user;"

# On every deploy, after pulling new code:
cd backend && flask db upgrade
```

## 4. HTTPS / HSTS

Terminate TLS at the reverse proxy or load balancer in front of Gunicorn.
Once all traffic is confirmed HTTPS, the app automatically adds
`Strict-Transport-Security` to every response that arrives over a secure
connection (`app/__init__.py::_register_security_headers`) — no extra
configuration needed on the Flask side beyond `SESSION_COOKIE_SECURE=1`.

## 5. Production security checklist

- [ ] `SECRET_KEY` is a long random value, unique per environment, not
      committed anywhere.
- [ ] `DATABASE_URL` points at PostgreSQL with a least-privilege role.
- [ ] `CORS_ORIGINS` lists only the real frontend origin(s) — no wildcard.
- [ ] `SESSION_COOKIE_SECURE=1` and the app is only reachable over HTTPS.
- [ ] `RATELIMIT_STORAGE_URI` points at Redis (not in-memory) if running
      more than one backend process/instance.
- [ ] `FLASK_DEBUG` is unset/`0` — debug mode must never be on in
      production.
- [ ] `UPLOAD_FOLDER` is on persistent, backed-up storage with correct
      filesystem permissions.
- [ ] Database backups are configured and restore has been tested (see
      below).
- [ ] `.env` files are excluded from version control (already covered by
      `.gitignore`) and secrets are supplied via your platform's secret
      manager / environment variables.

## 6. Backups and recovery

A full managed backup service is out of scope for this project (per the
instruction to avoid overengineering). Recommended minimal approach:

- **PostgreSQL**: daily `pg_dump` to encrypted, off-host storage, retained
  for at least 30 days. Most managed Postgres providers (RDS, Cloud SQL,
  Supabase, etc.) offer this as a built-in setting — enable it rather than
  building a custom job where possible.
- **Uploaded files** (`UPLOAD_FOLDER`): back up the same volume/bucket on
  the same schedule as the database, since `request_attachments` and
  `request_documents` rows reference files there by relative path.
- **Test restores** periodically (e.g. quarterly): restore the latest
  backup into a scratch database and confirm `flask db upgrade` (or a
  simple row-count check) succeeds against it.

## 7. Data retention

No specific retention periods were defined in the original specification,
so none are enforced automatically. Recommended defaults if none are
otherwise mandated by your organization's policy:

- Service requests, complaints, invoices, payments, and audit logs:
  retain indefinitely (they form the business/financial/audit record).
- Messages and notifications: safe to prune after 12–24 months if storage
  becomes a concern, since they are supplementary to the record above.
- Any deletion must respect foreign-key relationships and must not remove
  rows referenced by `audit_logs` — soft-deletion (an `is_active`/`
  deleted_at` flag) is preferable to hard deletion for business records.
