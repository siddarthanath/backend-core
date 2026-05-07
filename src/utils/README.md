# utils/

Shared utilities with no dependencies on other `src/` layers.

`logging.py` — `setup_logger(name)` returns a configured stdlib logger. No `print()` anywhere in the codebase. Migration to structlog planned for Round 3.