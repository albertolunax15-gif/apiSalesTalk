# ---------- Dockerfile ----------
FROM python:3.11.9-slim

# Configuración básica
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=10000

WORKDIR /app

# Instala dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Instala dependencias de Python con caché efectivo
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copia el resto del proyecto
COPY . .

# Exponer puerto (informativo localmente)
EXPOSE 10000

# Arranque (SHELL FORM) para que $PORT se expanda en Render
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT