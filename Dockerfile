# Evidence API image (issue #9). Installs the package from the lockfile and serves
# the FastAPI read paths with uvicorn. Kept deliberately small: no crawler extras
# are needed to serve evidence, only the API and its ledger/db dependencies.
FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    # The project uses the src/ layout without a packaging config (tests set
    # pythonpath=["src"]); the container takes the same route.
    PYTHONPATH=/app/src

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies from the lockfile first so application edits do not
# invalidate the dependency layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY src ./src
COPY config ./config
COPY db ./db
COPY scripts/start_api.sh ./scripts/start_api.sh
RUN uv sync --frozen --no-dev

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=20s \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["./scripts/start_api.sh"]
