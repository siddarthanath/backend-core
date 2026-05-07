# tests/

`unit/` — pure Python logic tests, no DB or HTTP. `integration/` — full stack tests using real Supabase DB and the ASGI test client.

No DB mocks. All integration tests require `DATABASE_URL` and Supabase credentials in the environment (set via GitHub Actions secrets in CI, `.env` locally). See `skills/backend-testing/SKILL.md` for fixture conventions.