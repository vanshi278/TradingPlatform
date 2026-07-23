# Combined production image for a single-service deploy (Render/Railway):
# builds the React dashboard and serves it from FastAPI alongside the REST API
# and WebSocket — one origin, one container. (Local dev still uses
# docker-compose with separate backend + nginx frontend services.)

# ---- stage 1: build the React dashboard ----
FROM node:18-alpine AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build                      # -> /fe/dist

# ---- stage 2: FastAPI backend + bundled frontend ----
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app

# lean runtime deps (all ship manylinux wheels -> no compiler needed).
# The heavy ML libs (torch/lightgbm/shap/matplotlib) are offline-only, excluded.
COPY backend/requirements-web.txt .
RUN pip install --upgrade pip && pip install -r requirements-web.txt

COPY backend/ ./
COPY db/ ./db
# bundle the built dashboard; FastAPI serves it at "/"
COPY --from=frontend /fe/dist ./static

EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
