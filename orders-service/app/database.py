"""
database.py
---------------
Configuración de la conexión a PostgresSQL para el Orders Service

El Orders Service tiene su PROPIA base de datos completamente
independiente del Catalog Service. Esto es el patrón
"Data base per Service" - uno de los principios fundamentales de los
microservicios.

¿Por qué bases de datos separadas?
- Independencia: si la DB del Catalog falla, Orders sigue funcionando
- Escalabilidad: puedes escalar cada DB según sus propias necesidades
- Libertad tecnológica: podrías usar MongoDB para Orders si quisieras
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "La variable DATABASE_URL no está configurada."
        "Verifica que tu archivo .env existe y tiene el valor correcto."
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=os.getenv("ENVIRONMENT") == "development",
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    """
    Generador que provee una sesión de DB a cada petición HTTP.
    FastAPI la cierra automáticamente al terminar cada petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_database_connection() -> bool:
    """
    Verifica que la conexión a la base de datos funciona.
    Se llama al iniciar la aplicación.
    """
    try: 
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return False