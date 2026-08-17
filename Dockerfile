# NeuroLLM -- single-container deployment (Hugging Face Spaces, or any
# generic Docker host). Builds the frontend, then serves both the UI and the
# API from one FastAPI process (see backend/app/main.py, which mounts
# frontend/dist and falls back to index.html for client-side routes) -- the
# same architecture run.sh uses locally, just containerized.
#
# This is a separate, additive Dockerfile from backend/Dockerfile and
# frontend/Dockerfile (used by docker-compose.yml for the two-service local
# dev setup) -- neither of those is changed by this file.

# ---- Stage 1: build the frontend -------------------------------------------
FROM node:20-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: backend + built frontend -------------------------------------
FROM python:3.11-slim
WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
# torch's default PyPI wheel bundles CUDA libraries even though this image
# is CPU-only (no GPU on HF Spaces' free tier) -- installing from the
# official CPU-only index first keeps the image several GB smaller. The
# plain `pip install -r requirements.txt` afterward sees torch already
# satisfies its version constraint and leaves it alone.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/app ./backend/app
COPY data ./data
COPY --from=frontend-build /build/frontend/dist ./frontend/dist

WORKDIR /app/backend

# Hugging Face Spaces (Docker SDK) expects the app to listen on the port
# named by `app_port` in the Space's README frontmatter (7860 here) --
# generic Docker hosts can override with `-e PORT=...`. ENABLE_LOCAL_MODEL=1
# is the default already (see app/config.py); the free HF Spaces CPU Basic
# tier (16GB RAM) is large enough to run it, just slower than a GPU/MPS
# machine since inference is CPU-only here.
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
