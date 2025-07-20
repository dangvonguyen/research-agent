FROM python:3.12-slim AS base

WORKDIR /app

RUN groupadd -r app && useradd -r -g app app

RUN mkdir -p /app/logs && chown -R app:app /app

RUN apt-get update && apt-get install -y curl

FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.6.1 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

COPY . .

FROM base AS runtime

COPY --from=builder --chown=app:app /app /app

USER app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

EXPOSE 8000
