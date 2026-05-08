"""Entry point — creates the FastAPI app via factory."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Internal
from src.core.factory import create_app

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

app = create_app()