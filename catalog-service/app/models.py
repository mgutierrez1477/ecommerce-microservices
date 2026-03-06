"""
models.py
-----------
Define las tablas de la base de datos como clases de Python

SQLALchemy lee estas clases y las traduce a tablas reales en PostgreSQL.
cada clase es una tabla. Cada atributo con Column() es una columna

Regla importante: los modelos describen CÓMO SE ALMACENAN los datos.
los schemas (que crearemos después) describen CÓMO VIAJAN por la API.
son responsabilidades diferentes y por eso van en archivo diferentes.
"""

import uuid #Sirve para generar identificadores unicos universales(IDs productos, IDs ordenes, etc)
from datetime import datetime # Trabaja con fechas, horas, registros, actualizaciones
from sqlalchemy.sql import func
from sqlalchemy import(
    Column, # Define una columna en la tabla
    String, # Tipo de texto con longitud máxima
    Text, # Tipo de texto sin límite de longitud
    Numeric, # Tipo numérico exacto (para dinero)
    Integer, # Tipo entero
    Boolean, # Tipo verdadero/Falso
    DateTime, # Tipo fecha y hora
)

from sqlalchemy.dialects.postgresql import UUID # identificador único nativo de PostgreSQL

# Importamos Base desde database.py
# Al heredar de Base, SQLALchemy sabe que esta clase es una tabla
from app.database import Base


class Product(Base):
    """
    Representa la tabla 'products' en PostgreSQL.
    ¿Por qué UUID como ID y no como un número entero(1,2,3....)?

    Los IDs numéricos tienen dos problemas:
    1. Son predecibles: si ves el producto con id=5, sabes que existen
    el 1,2,3,4. Un atacante puede iterar sobre todos los IDs para
    extraer datos
    2. En microservicios, si dos servicios crean registros independientemente
    y luego los sincronizas, los IDs númericos colisionan. Los UUID son únicos
    en el universo, nunca colisionan.

    UIID ejemplo: 550e8400-e29b-a716-446655440000
    """

    # __tablename__ define el nombre real de la tabla en PostgreSQL
    # Por convención, nombres de la tabla en minúsculas y plural
    __tablename__ = 'products'

    # ===============================
    # COLUMNA: ID
    # ===============================

    id = Column(
        # UUID es un tipo de nativo de PostgreSQL, más eficiente
        # que guarda el UUID como texto
        # as_uuid=True le dice a SQLALchemy que lo trate como
        # objeto UUID de python, no como string
        UUID(as_uuid=True),
        primary_key=True,
        # default=uuid.uuid4 significa: cuando sea crea un nuevo
        # registro y no se provee id, llama a uuid.uuid4() para
        # generarlo automáticamente en Python.
        # Nota: es uuid.uuid4 SIN paréntesis. le pasamos la función,
        # no el resultado. SQLALchemy la llamará cuando la necesite
        default=uuid.uuid4,
        nullable=False
    )

    # ==============================
    # COLUMNA: name
    # ==============================
    name = Column(
        String(200), #Máximo 200 caracteres
        nullable=False, # No puede estar vacío en la DB
        # index=True crea un índice en esta columna
        # Un índice es como el índice en un libro: en lugar de leer
        # toda la tabla para encontrar un producto por nombre,
        # PostgreSQL consulta el índice y va directo al registro.
        # Hace búsquedas mucho mas rápidas a costa de un poco
        # más de espacio en disco
        index=True,
    )

    # ==============================
    # COLUMNA: descripcion
    # ==============================
    descripcion = Column(
        # Text no tiene límite de longitud, ideal para descripciones
        # largas. String(n) tiene limite fijo.
        Text,
        # nullable:True significa que este campo es opcional.
        # Un producto puede no tener descripción.
        nullable=True,
    )

    # ================================
    # COLUMNA: price
    # ================================
    price = Column(
        # Nunca user Float para dinero. Los números flotantes tienen
        # problemas de precisión binaria. Por ejemplo:
        # >>> 0.1 + 0.2
        # 0.30000000000000004
        # Si acumulas ese error en miles de transacciones, el dinero
        # no cuadra. Numeric(10,2) es exacto siempre.
        # 10 =  total de dígitos permitidos
        # 2 = dígitos después del punto decimal
        # Permite precios hasta: 99,999,999.99
        Numeric(10,2),
        nullable=False,
    )

    # ==================================
    # COLUMNA: stock
    # ==================================
    stock = Column(
        Integer,
        nullable=False,
        # si no se especifica stock al crear, empieza en 0
        default=0,
    )

    # ===================================
    # COLUMNA: category
    # ===================================
    category = Column(
        String(100),
        nullable=True,
        # Índice porque filtraremos productos por categoría frecuentemente
        # GET /products?category=electronics
        index=True,
    )

    # =====================================
    # COLUMNA: is_active (Soft Delete)
    # =====================================
    # En lugar de borrar productos de la DB, los desactivamos.
    # Esto se llama "soft delete" (borrado suave)
    # ¿Por qué no borrar directamente?
    # Imagina que tienes órdenes que referencian un producto.
    # Si borras el producto, esas órdenes quedan con una referencia
    # a algo que ya no existe, Con soft delete, el producto sigue
    # en la DB pero invisible para los usuarios, El historial queda
    # intacto,
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    # =====================================
    # COLUMNAS: Auditoría (created_at, updated_at)
    # =====================================
    # Saber cuándo se creó y modificó cada registro es una
    # buena práctica básica. Ayuda a debuggear, a auditar cambios,
    # y a ordenar resultados cronológicamente.
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        # server_default=func.now() para poner la hora y no tener
        # complicaciones
        server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        # onupdate: se llama automáticamente cada vez que
        # el registro es modificado con db.commit()
        onupdate=func.now()
    )

    def __repr__(self):
        """
        Define cómo se muestra el objeto cuando lo imprimes.
        Solo para debugging. Sin esto verías algo como:
        <app.models.Product object at 0x7f123456789>
        con esto ves:
        <Product id=550e8400... name='Laptop' price=999.99>
        """
        return (
            f"<Product "
            f"id={self.id}"
            f"name='{self.name}'"
            f"price= {self.price}"
            f"stock= {self.stock}"
            f"active= {self.is_active}"
        )