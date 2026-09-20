# FamilyDB bot image. Build with `docker compose build`; run with `docker compose up -d`.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so editing the code does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Run as an unprivileged user; /data holds the database and the Google token.
RUN useradd --create-home --uid 1000 familydb \
    && mkdir -p /data \
    && chown familydb:familydb /data
USER familydb

ENV PATH="/app/.venv/bin:$PATH" \
    FAMILYDB_PATH=/data/familydb.sqlite3 \
    GOOGLE_TOKEN_PATH=/data/google_token.json

VOLUME ["/data"]
CMD ["familydb", "run"]
