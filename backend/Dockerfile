# --- builder: installs dependencies into a venv, isolated from the runtime
# image so pip's cache, wheel build artifacts, and (if a future dependency
# ever needs one) a C compiler never end up in what actually ships. ---
FROM python:3.13-slim AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# --- runtime: the image that actually runs in every environment (dev
# container, CI, production) - only the built venv and app code, nothing
# needed solely to build them. ---
FROM python:3.13-slim AS runtime

# Prevent .pyc files and force stdout/stderr to be unbuffered (so logs show up
# immediately in `docker compose logs`).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# libpq is required by psycopg at runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness only (no DB/Redis check) - see app/api/v1/endpoints/health.py for
# why liveness and readiness are deliberately separate checks.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/live')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
