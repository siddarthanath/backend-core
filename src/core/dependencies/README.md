# core/dependencies/

FastAPI dependency functions injected into handlers via `Depends()`.

`get_db` — yields an `AsyncSession` from the registry. `get_current_user` — decodes the Supabase JWT and returns `UserClaims`. Never instantiate sessions or decode tokens outside these dependencies.