"""
main.py
-------
Punto de entrada de la aplicación FastAPI

Es el archivo que une todas las piezas
- Crea la instancia de FastAPI 
- Registra los routers
- Configura middlewares
- Define el ciclo de vida (startup/shutdown)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, verify_database_connection
from app.routers import products

# ===============================
# CICLO DE VIDA
# ===============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Controla qué pasa cuando la aplicación inicia y cuando se apaga.

    El código ANTES del yield se ejecuta al INICIAR el servidor.
    El código DESPUÉS del yield se ejecuta al APAGAR el servidor.

    ¿Por qué asinccontextmanager?
    FastAPI moderno usa este patrón en lugar de los eventos
    @app.on_event("startup) que están deprecados desde FastAPI 0.93
    """
    # ----- AL INICIAR ---------------------------------
    print(" Iniciando Catalog Service....")

    # Verificamos que la DB está accesible antes de aceptar peticiones
    if not verify_database_connection():
        raise RuntimeError(
            "No se puede conectar a la base de datos."
            "Verifica que PostgreSQL está corriendo."
        )
    print("Conexión a PostgreSQL verificada")

    # Crea las tablas si no existen.
    # En producción real usaríamos Alembic para esto,
    # pero para desarrollo es conveniente tenerlo aquí.
    Base.metadata.create_all(bind=engine)
    print("Tablas verificadas")

    print("Catalog Service listo para recibir peticiones")

    yield # <- El servidor corre aquí

    # ----------- Al apagar -----------------
    print(" Catalog Service apagándose....")

# ===========================
# INSTANCIA DE FASTAPI
# ===========================
app = FastAPI(
    title="Catalog Service",
    description=("" \
    "Microservicio responsable del catálogo de productos. "
    "Gestiona la creación, consulta, actualización y desactivación "
    "de productos en el sistema de e-commerce. "
    ),
    version="1.0.0",
    lifespan=lifespan,
    # La documentación interactiva estará en /docs
    docs_url="/docs",
    # Documentación alternativa más limpia en /redoc
    redoc_url="/redoc",
)

# ==============================
# MIDDLEWARES
# ==============================
# CORS: Cross-Origin Resource Sharing
# Permite que un frontend en otro dominio haga peticiones a tu API.
# Sin esto, el navegador bloquea las peticiones por seguridad
#
# allow_origins=["*"] acepta peticiones de cualquier origen.
# En producción cambiarías esto a: ["https://tufrontend.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================
# REGISTRAR ROUTERS
# ================================
# include_router agrega todos los endpoints del router a la app.
# prefix="/api/v1" se suma al prefix="/products" del router
# Resultado: todos los endpoints están en /api/v1/products/..
#
# ¿por que /api/v1/?
# El "v1" permite versionar tu API. Si en el futuro cambias
# la estructura de los endpoints, creas /api/v2/ sin romper
# los clientes que usan /api/v1/.
app.include_router(products.router, prefix="/api/v1")

# =================================
# HEALTH CHECK
# =================================
@app.get("/health", tags=["health"])
def health_check():
    """
    Endpoint de salud del servicio.

    Los servicios de nube (GCP, AWS, KUBERNETES) llaman a este
    endpoint periódicamente para saber si el servicio está vivo.
    Si retorna 200, el servicio está saludable.
    Si falla o tarda demasiado, la nube puede reiniciar el 
    contenedor automáticamente.

    Siempre debe ser rápido y simple. No hagas queries a la DB aquí.
    """
    return {
        "status": "healthy",
        "service": "catalog-service",
        "version": "1.0.0",
    }
