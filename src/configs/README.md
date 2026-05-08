# configs/

Application configuration loaded from environment variables and `.env`.

All config lives in `settings/` — one file per concern (app, database, auth, external). Never hardcode secrets or URLs anywhere else in the codebase.