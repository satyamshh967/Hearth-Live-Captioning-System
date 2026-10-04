# Stage 1: Build Frontend PWA
FROM node:20-alpine AS frontend-builder
WORKDIR /app/apps/web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web ./
RUN npm run build

# Stage 2: Python Backend Runtime
FROM python:3.11-slim AS runtime

# Install audio dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY services/core/requirements.txt ./services/core/
RUN pip install --no-cache-dir -r services/core/requirements.txt

# Copy backend code, configs, and prompts
COPY services ./services
COPY configs ./configs
COPY prompts ./prompts

# Copy compiled frontend from builder
COPY --from=frontend-builder /app/apps/web/dist /app/apps/web/dist

# Expose single port for UI + API + WebSockets
EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV HEARTH_PROFILE=balanced

# Healthcheck verifying zero external network dependency
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "services.core.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
