# configs/settings/

Pydantic `BaseSettings` classes, one per concern. Each reads only the env vars it declares — no cross-pollution.

`__init__.py` exposes module-level singletons (`app_settings`, `database_settings`, etc.) — import the one you need, never instantiate a settings class directly.