# Imagen base
FROM python:3.11.9-slim

# Evitar archivos .pyc y forzar logs “unbuffered”
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=10000

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema mínimas (certificados, ca, curl para healthcheck opcional)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# Instala primero dependencias (mejor cache)
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copia el resto del proyecto
COPY . .

# Exponer (informativo; Render ignora EXPOSE, pero sirve localmente)
EXPOSE 10000

# (Opcional pero útil) healthcheck interno: Render tiene su propio check,
# pero esto te ayuda a detectar si la app dejó de atender dentro del contenedor.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" || exit 1

# Arranque: usa SIEMPRE $PORT (Render lo setea en runtime)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]