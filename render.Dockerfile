# NeuroLLM -- lightweight deploy target for free-tier hosts (Render's free
# 512MB web service, etc.) that can't run torch/transformers. Same unified
# single-process architecture as the root Dockerfile (frontend built once,
# served by FastAPI alongside the API), but installs requirements-lite.txt
# instead. ENABLE_LOCAL_MODEL=0 (set by render.yaml) hides "local_hf" from
# the UI -- the app runs on the mock provider only. See README.md's
# "Live demo" section for exactly what that does and doesn't include.

# ---- Stage 1: build the frontend -------------------------------------------
FROM node:20-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend (lite) + built frontend ------------------------------
FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements-lite.txt ./backend/requirements-lite.txt
RUN pip install --no-cache-dir -r backend/requirements-lite.txt

COPY backend/app ./backend/app
COPY data ./data
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

WORKDIR /app/backend

ENV PORT=10000
EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
