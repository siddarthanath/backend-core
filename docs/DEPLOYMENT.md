# Deployment — backend-core

Things to do (or know) before running this in production. The defaults are tuned
for local development; several need attention for a real deployment.

---

## 1. Environment

Copy `.env.example` to `.env` and fill every value. Critical points:

- **`SUPABASE_SERVICE_ROLE_KEY` is server-side only.** It bypasses Row Level Security
  and can delete any user. Never expose it to the frontend, never commit it, inject it
  as a secret in your host/CI.
- **`CORS_ORIGINS`** must list your real frontend origin(s) as a JSON array — the
  default `["http://localhost:3000"]` will block your deployed frontend.
- **`STRIPE_WEBHOOK_SECRET`** must match the signing secret of the webhook endpoint you
  register in the Stripe dashboard (`/api/v1/billing/webhook`).
- Run migrations on deploy: `alembic upgrade head`.

---

## 2. Rate limiting needs a shared store for multi-process

slowapi stores counters **in memory per process** (see `src/core/middleware/rate_limit.py`).
Run more than one worker (gunicorn `-w 4`, multiple pods) and each keeps its own
counters — the effective limit becomes ~N× the configured value, and every restart
resets them.

For real deployments, point slowapi at Redis:

```python
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[app_settings.RATE_LIMIT_DEFAULT],
    storage_uri=os.environ["REDIS_URL"],   # e.g. redis://:pass@host:6379/0
)
```

Add `REDIS_URL` to settings + `.env`. Not required for a single-process server.

---

## 3. Body-size limit assumes a Content-Length header

`BodySizeLimitMiddleware` rejects oversized requests by reading `Content-Length`.
A client can omit that header with chunked transfer-encoding (correctly rejected with
411) — but make sure your reverse proxy / load balancer (nginx, Cloud Run, etc.) also
enforces a max body size as defence in depth.

---

## 4. Enable Supabase account linking

Supabase Dashboard → Authentication → **enable "Allow linking of email and OAuth
accounts."** Without it, signing up via Google and via email with the same address
creates two separate auth users (two UUIDs) for one email. That triggers the
duplicate-email edge case in `upsert_from_supabase` — now handled gracefully with a
409 instead of a 500, but best avoided at the source.

---

## 5. Data retention — schedule the purge job

Account deletion **soft-deletes** the profile (keeps email + name so a failed Supabase
auth-delete can be retried). For GDPR/data-retention compliance you must hard-delete
that PII after a grace period:

```bash
python -m scripts.purge_deleted_users --days 30
```

Run it on a schedule (cron, a Supabase scheduled function, a CI cron workflow). Use
`--dry-run` to preview. Org/membership/subscription rows cascade automatically.

---

## 6. Transactional email (optional features)

Password reset works out of the box (the frontend uses Supabase's hosted flow). Two
features are disabled pending an email provider (e.g. Resend):

- **Email change** (`PUT /user/email`, commented out in `src/api/v1/user.py`) — needs a
  confirmation email to the new address. Re-enable per the comment there.
- Set `RESEND_API_KEY` when you wire these up.

---

## 7. Run behind HTTPS

The app sets baseline security headers (`SecurityHeadersMiddleware`) but assumes TLS is
terminated by your platform/reverse proxy. Don't serve it over plain HTTP — Supabase
session cookies and bearer tokens must never cross the wire unencrypted.
