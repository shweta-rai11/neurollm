# AI-Brain backend -- FastAPI app served by uvicorn.
# Simple single-stage build (no compiled/heavy build step needed).
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so this layer is cached unless requirements.txt changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application source.
COPY app ./app

# Directory for the SQLite database file so it can be mounted as a volume
# (see docker-compose.yml, which mounts a named volume here and points
# DATABASE_URL at it) without colliding with the /app code directory.
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
