# Usar imagen oficial ligera desde AWS Public ECR para evitar límites de Docker Hub en CodeBuild
FROM public.ecr.aws/docker/library/python:3.11-slim

# Evitar archivos .pyc y habilitar logs en tiempo real para CloudWatch
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2 y compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python aprovechando caché de capas Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente del microservicio
COPY application.py config.py ./
COPY models/ ./models/
COPY views/ ./views/

# Exponer el puerto 5000 requerido por el microservicio y el ALB en AWS Fargate
EXPOSE 5000

# Healthcheck nativo del contenedor hacia el endpoint /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Ejecutar servidor WSGI de producción Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "application:application"]
