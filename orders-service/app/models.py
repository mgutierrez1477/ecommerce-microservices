"""
models.py
------------
Define las tablas del Orders Service.

Tenemos dos tablas relacionadas:
- Order: la orden en sí (cleinte, total, estado)
- OrderItem:: cada producto dentro de la orden

Relación: Una Order tienes muchos OrdersItems (1 a N).

Patrón importante - Data Snapchot:
Cuando se crea una orden, copiamos el nombre y el precio del producto
en ese momento. ¿por qué? Porque si el precio del producto cambia mañana,
la orden histórica debe conservar el precio que tenía
cuando se compró. Y si el producto se elimina, la orden sigue teniendo
sus datos completos.
Este patrón se llama "snapshot" y es fundamental en microservicios
donde los servicios no comparten base de datos.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    Numeric,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

from app.database import Base

# =======================================
# ENUM DE ESTADOS DE ORDEN
# =======================================
class OrderStatus(str, enum.Enum):
    """
    Los estados posibles de una orden.

    Heredar de str además de enum.Enum permite que los valores
    del enum se serialicen como strings en JSON automáticamente.
    Sin str, Pydantic tendría problemas serializando el enum.

    El flujo normal de una orden es:
    pending -> confirmed -> shipped -> delivered
    Cualquier estado puede ir a cancelled.
    """
    PENDING = "pending"         # Orden creada, esperando confirmación
    CONFIRMED = "confirmed"     # Orden confirmada, stock reservado
    SHIPPED = "shipped"         # Orden enviada
    DELIVERED = "delivered"     # Orden entregada
    CANCELLED = "cancelled"     # Orden cancelada

# ======================================
# TABLA: orders
# ======================================
class Order(Base):
    """
    Representa una orden de compra completa.
    Contiene los datos del cliente y el estado general de la orden.
    Los productos específicos están en OrderItem.
    """

    __tablename__ = "orders"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # Email del cliente como identificador.
    # En un sistema real tendrías una tabla de usuarios.
    # pero para este proyecto el email es suficiente.
    customer_email = Column(
        String(200),
        nullable=False,
        index=True,
    )

    customer_name = Column(
        String(200),
        nullable=False,
    )

    # Estado actual de la orden usando el enum definido arriba
    status = Column(
        Enum(OrderStatus),
        nullable=False,
        default=OrderStatus.PENDING,
        index=True
    )

    # Total de la orden.
    # Se calcula sumando price * quantity de todos los OrderItems.
    # Lo guardamos aquí para no tener que recalcularlo cada vez.
    total = Column(
        Numeric(10,2),
        nullable=False,
        default=0,
    )

    # Dirección de envió
    shipping_address = Column(
        Text,
        nullable=True,
    )

    # Notas adicionales del cliente
    notes = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relación con OrderItem.
    # relationship() le dice a SQLALchemy que Order tiene muchos OrderItems.
    # back_populates="order" crea la relación inversa:
    # desde un OrderItem puedes acceder a su Order con item.order
    # cascade="all, delete-orphan" significa que si borrar una Order,
    # sus OrderItems se borran automáticamente también.
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return (
            f"<Order id={self.id}"
            f"customer={self.customer_email}"
            f"status={self.status}"
            f"total={self.total}>"
        )
    
# ===========================================
# TABLA: order_items
# ===========================================
class OrderItem(Base):
    """
    Representa un producto dentro de una orden.

    Puntos clave del diseño:
    1.- product_id guarda el UUID del produto en el Catalog Service
    pero NO es una foreign key real hacia esa tabla (proque está en otro
    servicio, en otra base de datos).

    2.- product_name y unit_price son snapshots: copiamos esos valores
    del Catalog en el momento de crear la orden.
    Si el producto cambia de nombre o de precio, la orden histórica
    conserva los valores originales.
    """

    __tablename__ = "order_items"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # FK hacia la tabla orders en ESTA misma base de datos
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    # UUID del producto en el Catalog Service
    # NO es FK proque está en otra base de datos
    # Es solo un valor de referencia
    product_id = Column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # Snapshot: nombre del producto al momento de la compra
    product_name = Column(
        String(200),
        nullable=False,
    )

    # Snapshot: precio unitario al momento de la compra
    unit_price = Column(
        Numeric(10,2),
        nullable=False,
    )
    quantity = Column(
        Integer,
        nullable=False,
        default=1,
    )

    # Subtotal de este item: unit_price * quantity
    # Lo calculamos y guardamos para no recalcular siempre
    subtotal = Column(
        Numeric(10,2),
        nullable=False,
    )

    # Relación inversa hacia Order
    order = relationship("Order", back_populates="items")

    def __repr__(self):
        return (
            f"<OrderItem product={self.product_name}"
            f"qty={self.quantity}"
            f"price={self.unit_price}"
        )