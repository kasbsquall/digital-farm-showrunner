# Full-stack image: builds the Next.js static export and serves it from the FastAPI
# backend, so the whole app runs as ONE container on ONE port (no CORS, no nginx).
# Build from the repo root:  docker build -t muckflix .

# ---- 1) build the frontend static export ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Same-origin API calls (the backend serves this bundle) — see frontend/lib/api.ts.
ENV NEXT_PUBLIC_API_URL=""
RUN npm run build

# ---- 2) backend that also serves the export at "/" ----
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=frontend /fe/out ./static_frontend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
