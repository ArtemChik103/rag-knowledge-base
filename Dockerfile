# Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Python Backend runtime
FROM python:3.11-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=7860

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy built frontend distribution
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy application source code
COPY backend/ ./backend
COPY tests/ ./tests
COPY LICENSE README.md SOLUTION_LOGIC.md ALGORITHM.md ./

# Create data directories with write permissions for Hugging Face user (uid 1000)
RUN mkdir -p chroma_data uploaded_docs models && chmod -R 777 chroma_data uploaded_docs models

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
