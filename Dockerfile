# ── Stage 1: Frontend build ──────────────────────────────────
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

# Install pnpm (pinned: pnpm@latest pulled 11.6.0 which is incompatible with
# node:20-alpine — ERR_UNKNOWN_BUILTIN_MODULE. Pin to the lockfile/dev version.)
RUN corepack enable && corepack prepare pnpm@11.4.0 --activate

# Install dependencies. pnpm 11 fails a frozen install when dependency build
# scripts are ignored (ERR_PNPM_IGNORED_BUILDS); allow them in this build stage
# (matches the original default-pnpm behavior; sharp etc. need their scripts).
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --config.dangerouslyAllowAllBuilds=true

# Build
COPY frontend/ ./
RUN pnpm build

# ── Stage 2: Backend dependencies ────────────────────────────
FROM python:3.13-slim AS backend-deps
WORKDIR /app/backend

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ── Stage 3: Production ─────────────────────────────────────
FROM python:3.13-slim AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    nodejs \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 appuser && useradd -u 1000 -g appuser -m appuser

WORKDIR /app

# Copy backend source first, then overlay clean venv from build stage
COPY backend/ /app/backend/
COPY --from=backend-deps /app/backend/.venv /app/backend/.venv

# Copy frontend standalone build
COPY --from=frontend-builder /app/frontend/.next/standalone /app/frontend/
COPY --from=frontend-builder /app/frontend/.next/static /app/frontend/.next/static
COPY --from=frontend-builder /app/frontend/public /app/frontend/public

# Copy entrypoint
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Create data directories and set ownership
RUN mkdir -p /app/data /app/backend/sample_docs && \
    chown -R appuser:appuser /app

USER appuser

ENV PATH="/app/backend/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PORT=3000

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f "http://localhost:${PORT:-3000}/" || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
