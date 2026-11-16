# Build context is the repository root: the API depends on the engine workspace package.
#   docker build -f backend/Dockerfile -t piscope-api .
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependencies first, so source edits do not invalidate this layer.
COPY pyproject.toml uv.lock ./
COPY engine/pyproject.toml engine/README.md engine/
COPY backend/pyproject.toml backend/README.md backend/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package piscope-api

COPY engine/src engine/src
COPY backend/src backend/src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package piscope-api

FROM python:3.12-slim
RUN useradd --create-home --uid 1000 piscope && mkdir /data && chown piscope:piscope /data
COPY --from=build --chown=piscope:piscope /app/.venv /app/.venv
COPY --chown=piscope:piscope backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PISCOPE_DATA_DIR=/data \
    PISCOPE_DIGITS=1000000
USER piscope
WORKDIR /app
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=120s --retries=5 \
    CMD python -c "import json,sys,urllib.request; sys.exit(0 if json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health'))['dataset_available'] else 1)"
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "piscope_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
