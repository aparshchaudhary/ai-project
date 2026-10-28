# Multi-stage Dockerfile for deploying Aura Voice Assistant on Render

# Stage 1: Build React Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Web Service Runtime
FROM python:3.11-slim
WORKDIR /app

# Install essential system audio and compiler libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    portaudio19-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application backend and root entrypoints
COPY backend/ ./backend/
COPY run.py .
COPY .env.example .

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV HOST=0.0.0.0
ENV PORT=10000
ENV RENDER=true

EXPOSE 10000

CMD ["python", "run.py"]
