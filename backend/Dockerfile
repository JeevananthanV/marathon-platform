# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production Runtime
FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system group and user
RUN addgroup --system --gid 1001 marathon \
    && adduser --system --uid 1001 --gid 1001 marathonuser

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/marathonuser/.local
ENV PATH=/home/marathonuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application source code
COPY --chown=marathonuser:marathon . .

# Ensure start script is executable
RUN chmod +x start.sh

# Switch to non-root user
USER marathonuser

EXPOSE 8000

# Native health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENTRYPOINT ["./start.sh"]
