"""
database.py 
Configura la conexión a PostgreSQL usando SQLALchemy.
Todo el resto de la aplicación importa 'SessionLocal' y 'Base' desde aquí.
"""
import os #Permite interactuar con variables del sistema operativo(variables de entorno)
from sqlalchemy import create_engine, text #create engine para conectar la base de datos y text para ejecutar consultar en segundo plano
from sqlalchemy.ext.declarative import declarative_base #Permite crear una clase base para definir modelos usando el orm de sqlalchemy
from sqlalchemy.orm import sessionmaker #Permite crear sesiones  para interactuar con la base de datos (queries, commits, etc)
from dotenv import load_dotenv #Permite cargar variables desde un archivo .env

# load_dotenv() lee el archivo .env y carga cada línea como
# variable de entorno. Si la variable ya existe en el entorno
# del sistema (como pasará dentro de Docker), no la sobreescribe.
# Esto permite que el mismo código funcione en local y en producción
# sin cambiar nada.
load_dotenv()

# Leemos la URL de conexión desde las variables de entorno
DATABASE_URL = os.getenv("DATABASE_URL")

#Si la DATABASE_URL tiene algun problema detiene el programa y manda el mensaje de erro
if not DATABASE_URL:
    raise ValueError(
        "La variable DATABASE_URL no esta configurada. "
        "Verifica que tu archivo .env existe y tiene el valor correcto"
    )

#create_engine crea el objeto central que gestiona la conexion
#con postgresql. no abre una conexión inmediatamente, solo
#configura cómo conectarse cuando sea necesario.
engine = create_engine(
    DATABASE_URL,
    
    #pool_pre_ping=True: antes de usar una conexión del pool,
    #SQLALchemy envia un "ping" a la DB para verificar que siga viva.
    #Evita errores cuando una conexión lleva mucho tiempo inactiva
    #y el servidor la cerró por inactividad
    pool_pre_ping=True,

    #pool_size: número de conexiones permanentes que mantiene abiertas.
    #tener conexciones pre-abiertas es más rápido que abrir una nueva
    #en cada petición HTTP
    pool_size=5,

    #max_overflow: conexiones extra que puede abrir si pool_size se llena.
    #si hay 15 peticiones simultáneas, puede abriar hasta 5+10=15 conexiones
    max_overflow=10,

    #echo=False en producción. si lo pones True, SQLALchemy imprime
    #en la terminal cada query SQL que ejecuta, útil para debuggear,
    #pero muy verboso para producción.
    echo=os.getenv("ENVIRONMENT") == "development",

)

# =====================================
# FABRICA DE SESIONES (SessionLocal)
# =====================================
# Una sesión es como una "Conversación" con la base de datos.
# Dentro de una sesión puedes hacer múltiples queries, y todos
# participan en la misma transacción

# SessionLocal es la clase (fábrica). cada ves que escribes
# SessionLocal() creas una nueva sesión independiente.

# autocommit=False: los cambios que hagas (INSERT, UPDATE, DELETE)
# no se guardan en la DB automáticamente tú decides cuándo
# confirmarlos con db.commit(). Esto te da control total: 
# si algo sale mal a la mitad , puedes hacer db.rollback() y 
# nada de los que hiciste se guarda

# autoflush=False: SQLALchemy no manda los cambios pendientes
# a la DB automáticamente antes de cada query. Tú controlas 
# cuándo pasa eso.

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ==============================
# LA BASE (base)
# ==============================

# Base es la clase de la que heredarán todos tus modelos.
# Cuando escribes 'class Product(base)', le estás diciendo
# a SQLALchemy: "esta clase representa una tabla en la DB".
# Base lleva el registro de todos los modelos para poder
# crear/verificar las tablas
Base = declarative_base()

# ==============================
# EL PROVEEDOR DE SESIONES (get_db)
# ==============================

def get_db():
    """
    Generador que provee una sesión de base de datos a cada petición http
    y garantiza que se cierre al terminar.

    Por qué es un generador (yield) y no una función normal (return)?
    FastAPI necesita ejecutar código DESPUÉS de que el endpoint
    termina. Con return, la función "pausa" en el yield, entrega
    la sesión, el endpoint la usa, y cuando el endpoint termina
    FastAPI "reanuda" esta función para ejecutar el bloque finally.

    El bloque finally garantiza que db.close() se ejecuta SIEMPRE, sin
    importar si el endpoint terminó bien o lanzó una excepción.
    sin esto, las conexiones quedarían abiertas hasta agotarse.

    Cómo se usa en un ednpoint:
        from fastapi import Depends
        from app.database import get_db

        def mi_endpoint(db: Session = Depends(get_db)):
            productos = db.query(Product).all()
            return productos

    FastAPI ve 'Depends(get_db)', llama a get_db(), toma lo que produce
    el yield (la sesión db), y la inyecta como argumento
    """

    db = SessionLocal()
    try: 
        yield db
    finally:
        db.close()

# ======================================
# FUNCIÓN DE VERIFICACIÓN
# ======================================

def verify_database_connection() -> bool:
    """
    Verifica que la conexión a la base de datos funciona.
    Se llama al iniciar la aplicación para fallar rápido
    si hay algún problema de configuración.

    'text()' es necesario en SQLALchemy 2.0 para ejecutar
    SQL crudo (strings). SELECT 1 es la query mas simple
    posible, solo verifica que hay conexión.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return False