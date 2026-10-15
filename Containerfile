# Pinned to the interpreter in .python-version (3.13).
FROM python:3.13-slim

# uv is the project's toolchain (uv.lock), so the image uses the same resolver as
# the local run instead of re-deriving a dependency set with pip.
COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /usr/local/bin/uv

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    CONFIA2_DATA_DIR=/app/data

# Dependencies first: they change far less often than the code, so this layer stays
# cached across rebuilds. --no-install-project keeps the package out of this step.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY scraper ./scraper
# The outreach template is read at run time and is edited by the owner, so it travels
# with the image. Measured: without it the container ingested prospects and then died on
# a bare ENOENT when asked to draft.
COPY templates ./templates
RUN uv sync --frozen --no-dev

# The job is a batch ingestion, not a service: it resolves the current SUSALUD
# resources, writes the prospect archive and exits. Schedule it with Cloud
# Scheduler or a systemd timer, not behind an HTTP server.
#
#   podman build -t confia2-scraper:dev .
#   podman run --rm -v ./data:/app/data:Z confia2-scraper:dev
#   podman run --rm -v ./data:/app/data:Z confia2-scraper:dev --include-procedures
ENTRYPOINT ["python", "-m", "scraper"]
