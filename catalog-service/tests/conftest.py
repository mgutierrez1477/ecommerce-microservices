"""
test/conftest.py
----------------
Configuración global de Pytest para el Catalog Service

Las fixtures definidas aquí están disponibles automáticamente
en todos los archivos de test sin necesidad de importarlas.

Estrategia de testing:
- Usamos SQLite en memoria en lugar de PostgreSQL real.
  SQLite no necesita servidor, vive en RAM, y se destruye
  al terminar cada test. Cada test empieza con DB limpia.
- Usamos TestClient de FastAPI para similar peticiones HTTP 
  sin levantar un servidor real
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

# =======================================
# CONFIGURACIÓN DE BASE DE DATOS DE PRUEBA
# =======================================


# URL de SQLite en memoria.
# "memory": significa que la DB vive en Ram, no en disco.
# No necesita PostgreSQL corriendo para los test
SQLITE_URL = "sqlite://"

# Creamos el motor de SQLite.
# StaticPool es necesario para SQLite en memoria porque garantiza
# que todas las conexiones usen la misma DB en memoria.
# Sin StaticPool, cada conexión crearía una DB separada y 
# los datos insertados en una no serían visibles en otra.
# connect_args={"check_same_thread": False} es requerido por SQLite
# cuando se usa en múltiples threads, que es el caso con FastAPI.
engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Fábrica de sesiones para los tests
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# =========================================
# FIXTURES
# =========================================

@pytest.fixture(scope="function")
def db_session():
    """
    Fixture que provee una sesión de DB limpia para cada test.

    scope="function" significa que esta fixture se ejecuta
    una ves POR CADA función de test. Así cada test tiene
    su propia DB vacía y los tests no se afectan entre sí.

    El flujo es: 
    1. Crea todas las tablas en SQLITE (vacías)
    2. Abre una sesión
    3. Entrega la sesión al test (yield)
    4. El test corre
    5. Cierra la sesión 
    6. Borra todas las tablas
    7. Listo para el siguiente test
    """
    # Crea las tablas en SQLite basándose en tus modelos
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Borra todas las tablas al terminar el test
        # Así el siguiente test empieza con DB limpia
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """
    Fixture que provee un cliente HTTP de prueba.

    Recibe db_session como argumento, lo que significa que
    Pytest ejecutará db_session primero y pasará el resultado aquí.
    Esto se llama "fixture dependency" (una fixture que depende de otra).

    La parte crítica es override_get_db.
    Tu app normalmente usa get_db() para obtener sesiones de PostgreSQL.
    Aquí le decimos: "cuando alguien pida una sesión DB, en lugar de
    conectarte a PostgreSQL, usa esta sesión de SQLite que ya tenemos."
    Esto se llama "dependency override" y es el mecanismo que hace
    posible testar sin PostgreSQL.
    """

    def override_get_db():
        """
        Reemplaza get_db() durante los tests.
        En lugar de abrir una conexión a PostgreSQL,
        devuelve la sesión de SQLite que ya tenemos.
        """
        try:
            yield db_session
        finally:
            pass # db_session ya maneja el cierre

    # Registra el override: cuando la app pida get_db, usa override_get_db
    app.dependency_overrides[get_db] = override_get_db

    # TestClient simula peticiones HTTP sin levantar servidor
    with TestClient(app) as test_client:
        yield test_client

    # Limpia el override al terminar para no afectar otros tests
    app.dependency_overrides.clear()