"""
crud.py 
------------
Operaciones de base de datos del Ordes Service.

La diferencia principal con el crud del Catalog Service es 
que aquí manejamos dos tablas relacionadas (Order y OrderItem)
y la lógica de creación es más compleja porque involucra
comunicación con el Catalog Service.
"""

import math
from uuid import UUID
from decimal import Decimal
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Order, OrderItem, OrderStatus
from app.schemas import OrderCreate, OrderStatusUpdate
from app import catalog_client

# =====================================
# READ - Obtener una orden por ID
# =====================================
def get_order_by_id(db: Session, order_id: UUID) -> Optional[Order]:
    """
    Busca una orden por su UUID.
    SQLALchemy carga automáticamente los items relacionados
    gracias a la realación definida en el modelo.
    """
    return (
        db.query(Order)
        .filter(Order.id == order_id)
        .first()
    )

# ========================================
# Read - Listar órdenes paginadas
# ========================================
def get_orders(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    customer_email: Optional[str] = None,
    status: Optional[OrderStatus] = None
) -> Tuple[List[Order], int]:
    """
    Lista de órdenes con filtros opcionales y paginación.
    """
    query = db.query(Order)

    if customer_email:
        query = query.filter(
            Order.customer_email == customer_email.lower()
        )
    
    if status:
        query = query.filter(
            Order.status == status
        )
    
    total = query.with_entities(func.count(Order.id)).scalar()

    offset = (page - 1) * page_size

    orders = (
        query
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return orders, total

# ========================================
# CREATE - Crear una nueva orden
# ========================================
def create_order(
        db: Session,
        order_data: OrderCreate,
) -> Tuple[Optional[Order], Optional[str]]:
    """
    Crea una nueva orden verificando stock en el Catalog Service

    Retonar una tupla (orden, error):
    - (Order, None) -> orden creada exitosamente
    - (None, str)   -> error con mensaje descriptivo

    El flujo es:
    1. Para cada item, consultar el Catalog Service
    2. Si algún producto no está disponible, retornar error
    3. Si todo está disponible, crear la orden y sus items
    4. Calcular el total sumando los subtotales

    ¿Por qué retornar (None, error_msg) en lugar de lanzar una excepción?
    Porque el error de "stock insuficiente" es un error de negocio
    esperado, no un error técnico inesperado. El router lo manejará
    retornando un 400 con el mensaje descriptivo.
    """

    # Paso 1: verificar disponibilidad de todos los items
    # Lo hacemos ANTES de crear nada en DB.
    # Si un item no está disponible, no queremos haber creado
    # la orden parcialmente.
    items_info = []

    for item in order_data.items:
        available, product_info = catalog_client.get_product_info(
            item.product_id,
            item.quantity,
        )

        if not available:
            if product_info is None:
                return None, (
                    f"El producto con id '{item.product_id}'"
                    f"no existe o no está disponible"
                )
            else:
                return None, (
                    f"Stock insuficiente para '{product_info['product_name']}'. "
                    f"Disponible: {product_info['available_stock']}, "
                    f"Solicitado: {item.quantity}"
                )
        
        items_info.append({
            "product_id": item.product_id,
            "product_name": product_info["product_name"],
            # El precio viene del Catalog Service (fuente de verdad)
            "unit_price": Decimal(str(product_info.get("available_stock", 0))),
            "quantity": item.quantity,
        })

        # Paso 2: obtener precios reales del Catalog Service
        items_witch_prices = []
        total = Decimal("0")

        for i, item in enumerate(order_data.items):
            price_data = catalog_client.get_product_price(item.product_id)

            if price_data is None:
                return None, (
                    f"No se pudo obtener el precio del producto"
                    f"'{items_info[i]['product_name']}'"
                )
            
            unit_price = Decimal(str(price_data))
            subtotal = unit_price * item.quantity
            total += subtotal

            items_witch_prices.append({
                "product_id": item.product_id,
                "product_name": items_info[i]["product_name"],
                "unit_price": unit_price,
                "quantity": item.quantity,
                "subtotal": subtotal,
            })

        db_order = Order(
            customer_email=order_data.customer_email,
            customer_name=order_data.customer_name,
            shipping_address=order_data.shipping_address,
            notes=order_data.notes,
            total=total,
            status=OrderStatus.PENDING,
        )

        db.add(db_order)
        # flush() envía el INSERT a la DB dentro de la transacción
        # pero SIN hacer commit todavía. Esto nos da el id de la orden
        # para poder asignarlo a los OrderItems.
        db.flush()

        # Paso 4: crear los items de la orden
        for item_data in items_witch_prices:
            db_item = OrderItem(
                order_id=db_order.id,
                **item_data,
            )
            db.add(db_item)

        # Paso 5: confirmar toda la transacción de una ves
        # Si algo falla aquí, PostgreSQL hace rollback de la orden
        # Y de todos los items. No quedan registros huérfanos.
        db.commit()
        db.refresh(db_order)

        return db_order, None
    
# ========================================
# UPDATE - Actualizar estado de una orden
# ========================================
def update_order_status(
        db: Session,
        order_id: UUID,
        status_data: OrderStatusUpdate,
) -> Optional[Order]:
    """
    Actualiza el estado de una orden.
    Es la única actualización permitida después de crear la orden.
    """
    db_order = get_order_by_id(db, order_id)

    if db_order is None:
        return None
    
    db_order.status = status_data.status
    db.commit()
    db.refresh(db_order)

    return db_order