"""
alembic/env.py
--------------
Configuración del entorno de Alembic

Este archivo le dice a Alembic dos cosas fundamentales:
1. Cómo conectarse a la base de datos
2. Dónde están los modelos para detectar cambios automáticamente

La parte más importante es 'target_metadata = Base.metadata'.
Esto le permite a Alembic comparar el estado actual de la DB
contra tus modelos y generar las migraciones automáticamente.
"""

import os
from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy import pool
from dotenv import load_dotenv

from alembic import context

# Cargamos el .env para leer DATABASE_URL
load_dotenv()

# Importamos Base y todos los modelos
# Es crítico importar los modelos aquí paara que Alembic
# los conozca y pueda detectar cambios
from app.database import Base
from app.models import Product

# Configuración de loggin de Alembic (viene del alembic.ini)
config =  context.config

# Verifica que el archivo alembic.ini exista
# fileConfig configura los logs usando ese archivo
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata es lo más importante de este archivo.
# Le dice a Alembic el "estado deseado" de la DB según tus modelos.
# Alembic compara ese estado deseado contra el estado actual de la DB
# y genera los cambios necesarios (ALTER TABLE, ADD COLUNM, etc.)
target_metadata = Base.metadata

# Sobreescribimos la URL de conexión con la del .env
# Así no tienes la contraseña hardcodeada en alembic.ini
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL")
)

def run_migrations_offline() -> None:
    """
    Modo offile: genera el SQL de las migraciones sin conectarse
    a la DB. Útil para revisar qué cambios se harán antes de aplicarlos.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url = url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """
    Modo online: se conecta a la DB y aplica las migraciones directamente.
    Es el modo que usarás normalmente
    """
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL no está definida")

    connectable = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
