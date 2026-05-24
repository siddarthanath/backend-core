FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ ./src/

RUN pip install --no-cache-dir -e .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ── Build & run ───────────────────────────────────────────────────────────────
# docker build -t backend-core .
# docker run -p 8000:8000 --env-file .env backend-core
#
# ── Recommended .dockerignore ─────────────────────────────────────────────────
# .env
# .venv
# __pycache__
# *.pyc
# tests/
# alembic/
# .git
