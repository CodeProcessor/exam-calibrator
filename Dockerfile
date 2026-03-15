FROM python:3.13-slim

WORKDIR /app

# Install uv via pip
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY src/ src/

# Install dependencies (no dev)
RUN uv sync --frozen --no-dev

# Data directory for shared SQLite DB (used by docker-compose volume)
RUN mkdir -p /app/data

WORKDIR /app/src
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "fast_api:app", "--host", "0.0.0.0", "--port", "8000"]
