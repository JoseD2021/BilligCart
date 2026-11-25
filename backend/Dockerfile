FROM python:3.14-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Stage solo para CI/desarrollo: agrega pytest y demás herramientas
FROM base AS test
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Stage final (es el que se construye por defecto con docker compose build)
FROM base AS production
EXPOSE 8000
CMD ["python", "run.py"]