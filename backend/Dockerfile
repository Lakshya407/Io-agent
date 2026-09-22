FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr so logs
# reach the container output promptly.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so the layer is cached unless requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application, migrations and configuration only.
COPY alembic.ini ./
COPY app ./app
COPY migrations ./migrations

EXPOSE 8000

# Apply migrations on startup, then serve. Uvicorn is run with a single worker
# behind a load balancer in production; scale horizontally by replicating.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
