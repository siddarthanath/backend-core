# tests/

`unit/` — pure Python logic tests, no DB or HTTP. `integration/` — full stack tests using real Supabase DB and the ASGI test client.

No DB mocks. All integration tests require `DATABASE_URL` and Supabase credentials in the environment (set via GitHub Actions secrets in CI, `.env` locally). See `skills/backend-testing/SKILL.md` for fixture conventions.

## Billing — live Stripe smoke test (manual, pre-merge)

Unit tests mock Stripe and cannot catch timing-dependent webhook issues. Before merging any billing change, run the full flow manually:

```bash
# Terminal 1 — backend
uvicorn src.main:app --reload

# Terminal 2 — Stripe CLI
stripe listen --forward-to localhost:8000/api/v1/billing/webhook

# Terminal 3 — trigger a checkout
# Open the app, go through checkout with a Stripe test card (4242 4242 4242 4242)
# Verify in backend logs:
#   billing.webhook_received event_type=customer.subscription.created
#   billing.subscription_activated org_id=<uuid> plan=pro
#   billing.webhook_received event_type=checkout.session.completed
# Verify in DB: subscription row has plan=pro, status=active, current_period_end set
```