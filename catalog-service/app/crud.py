"""
crud.py 
---------------
Contiene todas las operaciones de base de datos del Catalog Service.

Responsabilidad única: hablar con PostgreSQL
No sabe nada de HTTP, no sabe nada de peticiones ni respuestas.
Solo recibe datos, hace operaciones en la DB, y devuelve resultados.

Los routers importan estas funciones y las llaman cuando llega una
petición HTTP.
"""

from uuid import UUID
from typing import Optional, Tuple, List
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Product
from app.schemas import ProductCreate, ProductUpdate

# =============================================
# READ - obtener un producto por ID
# =============================================
def get_product_by_id(db: Session, product_id: UUID) -> Optional[Product]:
    """
    Busca un producto por su UUID en la base de datos.

    Parámetros:
    db -> la sesión de base de datos (viene del get_db())
    product_id -> el UUID del producto a buscar

    Retorna:
        El objeto Product si existe, None si no se encuentra.
        El router decide qué hacer con ese None (normalmente lanzar 404).

    Cómo funciona la query:
        db.query(Product)           -> SELECT * FROM products
        .filter(Product.id == id)   -> WHERE id = 'uuid-aqui'
        .firts()                    -> LIMIT 1, retorna el primero o None        
    """

    return (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

# ===============================================
# READ - Obtener lista paginada de productos
# ===============================================
def get_products(
        db: Session,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        only_active: bool = True,
)   -> Tuple[List[Product], int]:
    """
    Obtiene una lista paginada de productos con filtros opcionales.

    Párametros:
        db          -> sesión de base de datos
        page        -> número de página (empieza en 1)
        page_size   -> cuántos productos por página
        category    -> filtrar por categoría(opcional)
        only_active -> si TRUE, solo devuelve productos activos

    Retorna:
        Una tupla con dos elementos:
        - Lista de objetos Product
        - Total de productos que conciden con los filtros
        (sin paginar, para que el cliente calcule las páginas)
    
    ¿Por qué devolver el total de además de la lista?
    Si tienes 150 productos y pides la página 1 con 20 por página,
    recibes 20 productos. Pero sin el total (150), no sabes si hay más
    páginas. Con el total puedes calcular: 150/20 = 8 páginas
    """

    # Construimos la query base
    # Aún no se ejecuta en la DB, SQLALchemy espera hasta que
    # llamemos a .all() o .scalar()
    query = db.query(Product)

    # Aplicamos filtros opcionales
    # Cada .filter() agrega un AND a la query SQL
    if only_active:
        # SELECT * FROM products WHERE is_active = TRUE
        query = query.filter(Product.is_active == True)
    
    if category:
        # AND category = 'electronics'
        # Comparemos en minúsculas porque el validador de schemas
        # ya guardo la categoría en minúsculas
        query = query.filter(Product.category == category.lower())

    # Contamos el total de ANTES de paginar
    # Si paginaras primero y luego contaras, obtendrías el total 
    # de la página (20), no el total real (150)
    #
    # func.count() es una función de SQL: SELECT COUNT(id) FROM products
    # .scalar() ejecuta la query y devuelve un solo valor (el número)
    total = query.with_entities(func.count(Product.id)).scalar()

    # Calculamos el offset (cuántos registros saltar)
    # Página 1: (1-1) * 20 = 0      -> empieza desde el registro 0
    # Página 2: (2-1) * 20 = 20     -> salta los primeros 20
    # Página 3: (3-1) * 20 = 40     -> salta los primeros 40
    offset = (page - 1) * page_size

    products = (
        query
        # Ordenamos por fecha y creación descendente
        # Los productos más recientes aparecen primero
        .order_by(Product.created_at.desc())
        # OFFSET n -> salta los primeros n registros
        .offset(offset)
        # LIMIT n -> devuelve máximos n registros
        .limit(page_size)
        # Ejecuta la query y devuelve todos los resultados como lista
        .all()
    )

    return products, total

# ======================================
# CREATE - Crear un nuevo producto
# ======================================
def create_product(db:Session, product_data: ProductCreate) -> Product:
    """
    Crea un nuevo producto en la base de datos:

    Parámetros:
        db              -> sesión de base de datos
        product_data    -> schema de ProductCreate  con los datos validados

    Retorna:
        El objeto Product recién creado, con id y timestamps generados

    El flujo es siempre el mismo al crear:
        1. Convertir el Schema Pydantic a un objeto del modelo SQLALchemy
        2. Registrar el objeto en la sesión con db.add()
        3. Confirmar los cambios en la DB con db.commit()
        4. Refrescar el objeto para obtener los valores generados por la DB
    """

    # .model_dump() convierte el schema de Pydantic a un diccionario Python:
    # {"name": "laptop", "price": Decimal("999.99"), "stock":10, ...}
    #
    # **product_data.model_dump() desempaqueta ese diccionario como
    # argumentos nombrados para el constructor de Product:
    # Product(name="Laptop", price=Decimal("999.99"), stock=10, ...)
    db_product = Product(**product_data.model_dump())

    # db.add() registra el objeto en la sesión de SQLALchemy.
    # En este momento el producto NO está en la DB todavía.
    # SQLALchemy lo tiene en memoria y sabe que debe insertarlo.
    db.add(db_product)

    # db.commit confirma la transacción y ejecuta el INSERT en PostgreSQL
    # Si algo falla aquí, PostgreSQL hace rollback automáticamente
    # y los cambios no se guardan
    db.commit()

    # db.refresh() recarga el objeto desde la DB.
    # Es necesario porque después del commit, el objeto en memoria
    # no tiene los valores que generó PostgreSQL:
    # - El id (UUID generado por python pero confirmado por la DB)
    # - created_at y updated_at (generados por PostgreSQL con fun.now())
    # Sin el refresh(), esos campos estarían vacíos en el objeto.
    db.refresh(db_product)

    return db_product

# ======================================
# UPDATE - Actualizar un producto existente
# =======================================
def update_product (db: Session, product_id: UUID, product_data: ProductUpdate) -> Optional[Product]:
    """
    Actualiza los campos de un producto existente.
    Solo modifica los campos que se enviaron, no todos.

    Parámetros:
        db              -> sesión de base de datos
        product_id      -> UUID del producto a actualizar
        product_data    -> schema ProductUpdate con los campos a cambiar

    Retorna:
        El objeto Product actualizado, o None si no existe.
    """

    # Primero verificamos que el producto existe
    db_product = get_product_by_id(db, product_id)

    if db_product is None:
        return None
    
    # Model_dump(exclude_unset=True) es la clave de la actualización parcial.
    #
    # exclude_unset=True devuelve SOLO los campos que el cliente
    # envió explícitamente en el JSON. Los campos que no se enviaron
    # (y que tienen valor None por defecto) no aparecen en el dict
    #
    # sin exclude_unset=True:
    #  Cliente manda {"name": "Nuevo nombre"}
    #  model_dump() devuelve: {"name": "Nuevo nombre", "price": None,
    #                           "stock": None, "category": None}
    #  Resultado: sobreescribes price, stock, category con None <- MALO
    #
    # Con exclude_unset=True
    #  Cliente manda {"name": "Nuevo nombre"}
    #   model_dump() devuelve: {"name": "Nuevo nombre"}
    #   Resultado: solo actualizar el nombre <- CORRECTO

    update_data = product_data.model_dump(exclude_unset=True)

    # Aplicamos cada cambio al objeto SQLALchemy
    # setattr(objeto, "campo", valor) es equivalente a objeto.campo = valor
    # pero funciona cuando el nombre del campo es una variable
    for field, value in update_data.items():
        setattr (db_product, field, value)
    
    # Guardamos los cambios en la DB
    db.commit()
    db.refresh(db_product)

    return db_product

# ============================================
# DELETE - Desactivar un producto (soft delete)
# ===========================================
def deactivate_product(db: Session, product_id: UUID,) -> Optional[Product]:
    """
    Desactiva un producto marcándolo como inactivo.
    NO borra el registro de la DB (soft delete).

    ¿Por qué soft delete?
    Si borras el producto directamente, cualquier orden que lo 
    referencia queda con un ID que no existe. Con soft delete
    el producto sigue en la DB pero no aparece en las búsquedas 
    normales. El historial queda intacto

    Retonar: 
        El objeto Product con is_activa=False, o None si no existe
    """

    db_product = get_product_by_id(db, product_id)

    if db_product is None:
        return None
    
    db_product.is_active = False
    db.commit()
    db.refresh(db_product)

    return db_product

# =======================================
# STOCK - Verificar disponibilidad
# =======================================
def check_stock_availability(db: Session, product_id: UUID, requested_quantity: int,) -> Tuple[bool, Optional[Product]]:
    """
    Verifica si hay suficiente stock para una cantidad solicitada.

    Esta función la usará el Ordes Service cuando alguien
    intente crear una orden. Antes de confirmarla, Orders pregunta
    al Catalog Service si hay stock suficiente.

    Parámetros:
        db                  -> sesión de base de datos
        product_id          -> UUID del producto a verificar
        requested_quantity  -> cuántas unidades se quieren comprar

    Retorna:
        Tupla (hay_stock_suficiente, producto_o_None)
        - (True, Product)   -> hay stock, se puede hacer la orden
        - (False, Product)  -> no hay stock suficiente
        - (False, None)     -> el producto no existe o está inactivo
    """
    product = get_product_by_id(db, product_id)

    # Si el producto no existe o está desactivado, no hay stock
    if product is None or not product.is_active:
        return False, None
    
    has_stock = product.stock >= requested_quantity
    return has_stock, product

# ===================================
# STOCK - Reducir stock al confirmar orden
# ===================================

def reduce_stock(db: Session, product_id: UUID, quantity: int,) -> Optional[Product]:
    """
    Reduce el stock de un producto cuando se confirma una orden.

    Esta función la llamará el Orders Service después de crear
    una orden exitosamente.

    Parámetros:
        db          -> sesión de base de datos
        product_id  -> UUID del producto
        quantity    -> cuántas unidades se vendieron

    Retorna:
        El Product con stock actualizado, o None si no existe.

    Lanza: 
        ValueError si no hay suficiente stock.
        Esto no debería pasar si se verificó el stock antes,
        pero es una red de seguridad por si dos órdenes llegan
        al mismo tiempo
    """ 

    product = get_product_by_id(db, product_id)

    if product is None:
        return None
    
    if product.stock < quantity:
        raise ValueError(
            f"Stock insuficiente. "
            f"Disponible: {product.stock} "
            f"Solicitado: {quantity}"
        )
    
    product.stock -= quantity
    db.commit()
    db.refresh(product)

    return product