"""
schemas.py 
------------------
Define la forma de los datos que entran y salen del Orders Service.

Schemas de entrada (lo que el cliente manda):
    OrderItemCreate     -> un producto dentro de la orden
    OrderCreate         -> la orden completa con sus items

Schemas de respuesta (lo que el servidor devuelve):
    OrderItemResponse   -> item con todos sus datos
    OrderResponse       -> orden con sus items y metadatos
    OrderListResponse   -> Lista paginada de órdenes
"""

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, EmailStr

from app.models import OrderStatus

# ===================================
# SCHEMAS DE ITEMS
# ===================================
class OrderItemCreate(BaseModel):
    """
    Lo que el cliente manda para cada producto en la orden.
    Solo necesita el ID del producto y la cantidad.
    El nombre y precio los obtiene el servidor del Catalog Service.
    """

    product_id : UUID = Field(
        ...,
        description="UUID del producto en el Catalog Service"
    )

    quantity: int = Field(
        ...,
        ge=1,
        description="Cantidad a comprar. Mínimo 1.",
    )

class OrderItemResponse(BaseModel):
    """Lo que el servidor devuelve para cada item de la orden."""

    id: UUID
    product_id: UUID
    product_name: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal

    # Esto hace que pydantic pueda leer objetos no solo diccionarios
    model_config = {"from_attributes": True}

# ===========================================
# SCHEMAS DE ORDEN
# ===========================================
class OrderCreate(BaseModel):
    """
    Lo que el cliente manda para crear una orden.
    Debe incluir al menos un item.
    """

    customer_email: EmailStr = Field(
        ...,
        description="Email del cliente",
        examples=["cliente@ejemplo.com"],
    )

    customer_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Nombre completo del cliente",
        examples=["Juan García"],
    )

    items: List[OrderItemCreate] = Field(
        ...,
        min_length=1,
        description="Lista de productos a comprar. Mínimo 1 item",
    )

    shipping_address: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Dirección de envío"
    )

    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Notas adicionales para la orden",
    )

    @field_validator("customer_email")
    @classmethod
    def email_must_be_valid(cls,value: EmailStr) -> EmailStr:
        """Normaliza el email a minúsculas y verifica formato básico"""
        value = value.strip().lower()
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("El email no tiene un formato válido")
        return value
    
    @field_validator("customer_name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("El nombre no puede ser solo espacios")
        return stripped
    
    @field_validator("items")
    @classmethod
    def items_must_not_be_empty(cls, value: List) -> List:
        if len(value) == 0:
            raise ValueError("La orden debe tener al menos un item")
        return value
        
class OrderStatusUpdate(BaseModel):
    """
    Schema para actualizar solo el estado de una orden.
    Es el único campo que se puede cambiar después de crear la orden.
    """

    status: OrderStatus = Field(
        ...,
        description="Nuevo estado de la orden",
    )

class OrderResponse(BaseModel):
    """Lo que el servidor devuelve al consultar una orden."""
    
    id: UUID
    customer_email: EmailStr
    customer_name: str
    status: OrderStatus
    total: Decimal
    shipping_address: Optional[str]
    notes: Optional[str]
    items: List[OrderItemResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class OrderListResponse(BaseModel):
    """Lista paginada de órdenes con metadatos."""

    items: List[OrderResponse]
    total: int = Field(description="Total de órdenes")
    page: int = Field(description="Página actual")
    page_size: int = Field(description="Órdenes por página")
    pages: int = Field(description="Total de páginas")

    model_config = {"from_attributes": True}