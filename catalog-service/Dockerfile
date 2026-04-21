# ========================================
# ETAPA 1: BUILDER
# ========================================
# Usamos python:3.11-slim como base.
# slim es una versión reducida de la imagen oficial de Python.
# Tiene lo mínimo necesario para correr Python sin herramientas
# de desarrollo ni documentación. Pesa -150MB vs -900MB de la completa.
FROM python:3.11-slim AS builder 

# WORDIR define el directorio de trabajo dentro del contenedor.
# Todos los comandos siguientes se ejecutan desde aquí.
# Si no existe, Docker lo crea automáticamente.
WORKDIR /app

# Primero copiamos SOLO el requirements.txt y lo instalamos.
# ¿Por qué antes que el código?
# Docker construye las imágenes en capas. Cada instrucción es una capa.
# Docker cachea las capas que no cambiaron.
# El requirements.txt cambia raramente. Tu código cambia frecuentemente.
# Si copias el código primero, cualquier cambio en el código invalida
# la capa de instalación y Docker reinstala todo desde cero.
# Con este orden, solo reinstala cuando cambia requirements.txt.
COPY requirements.txt .

# Instalamos las dependecias en una carpeta específica.
# --no-cache-dir: no guarda caché de pip, reduce el tamaño de la imagen.
# --prefix=/install: instala en /install en lugar de la ubicación
# default de Python. Esto facilica copiar solo las dependencias
# a la etapa final sin llevarnos nada extra.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ==========================================
# ETAPA 2: FINAL
# ==========================================
# Empezamos desde la misma imagen base limpia.
# Esta etapa NO tiene el caché de pip ni los archivos temporales
# que se generaron durante la instalación en el builder.
FROM python:3.11-slim AS final

WORKDIR /app

# Copiamos las dependencias instaladas desde el builder.
# /install/lib/python3.11/site-packages contiene todas las librerías.
# Las copiamos al site-packages del Python de esta etapa final.
COPY --from=builder /install /usr/local

# Ahora copiamos el código de la aplicación.
# El punto final (.) significa "copia todo al WORKDIR (/app)".
# Esto incluye la carpeta app/, alembic/, alembic.ini, etc.
COPY . .

# Creamos un usuario sin privilegios para correr la aplicación.
# Por defecto los contenedores corren como root, lo cual es
# un riesgo de seguridad. Si alguien explota una vulnerabilidad
# en tu app y obtiene acceso al contenedor, tendría acceso root.
# Con un usuario sin privilegios, el daño potencial es limitado.
RUN adduser --disabled-password --gecos "" appuser

# Cambiamos al usuario sin privilegios
USER appuser

# Documentamos en qué puerto escucha el servicio.
# EXPOSE no abre el puerto, solo lo documenta.
# El puerto real se configura cuando corres el contenedor.
EXPOSE 8001

# El comando que se ejecuta cuando arranca el contenedor.
# Usamos la forma de array ["cmd", "arg1", "arg2"] en lugar de
# string "cmd arg1 arg2" porque la forma de array no pasa por
# un shell intermedio, es más eficiente y maneja mejor las señales
# del sistema operativo (como Ctrl+c o docker stop)
# 
# --host 0.0.0.0: escucha en todas las interfaces de red del contenedor.
# Sin esto, uvicorn solo escucharía en localhost del contenedor
# y no sería accesible desde fuera.
# --port 8001: el puerto donde corre el servicio.
# --workers 2: dos procesos para manejar peticiones en paralelo
# En producción usarías más workers según los cores del servidor.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
