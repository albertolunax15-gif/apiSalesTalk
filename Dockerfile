FROM python:3.11.9-slim

# Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# Asegurar que Python pueda encontrar el paquete "app"
ENV PYTHONPATH=/app

# Copiar los archivos del proyecto
COPY . .

# Instalar dependencias
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Exponer el puerto
EXPOSE 10000

# Ejecutar la aplicación apuntando al módulo correcto (app/main.py)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]