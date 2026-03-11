"""
schemas. py
-------------------
Define la forma que deben tener los datos que entran y salen de la API.
Pydantic valida automáticamente que los datos cumplan estos esquemas.

Si los datos no cumplen el esquema, FastAPI rechaza la petición
automáticamente con un error 422 (Un processable Entity) antes de
que llegue a tu logica de negocio. Tú no tienes que escribir
esa validación manualmente.

Patrón de herencia:
    ProductBase -> campos comunes
    ProductCreate -> lo que el cliente envía para CREAR
    ProductUpdate -> lo que el cliente envía para ACTUALIZAR
    ProductResponse -> lo que el servidor devuelve
"""

from decimal import Decimal
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

# ============================
# BASE
# ============================

class ProductBase(BaseModel):
    """
    Campos compartidos entre el schema de creación y el de respuesta.
    Esta clase no se directamente en ningún endpoint.
    Solo existe para que ProductCreate y ProductResponse hereden de ella
    y no tengamos que repetir los mismos campos dos veces.

    Field() nos permite agregar reglas de validación y metadata a cada campo.
    La metadata como 'description' y 'examples' aparece en la documentación
    qué se espera en cada campo sin tener que preguntarte.
    """

    name: str = Field(
        # Los ... (Ellipsis) significan que el campo es OBLIGATORIO.
        # Si el cliente no lo manda, Pydantic rechaza la petición.
        ...,
        min_length=1,
        max_length=200,
        description="Nombre del producto",
        examples=["Laptop Gaming ASUS ROG"],
    )

    description: Optional[str] = Field(
        # default=None significa que es opcional.
        # Si el cliente no lo manda, el valor será None.
        default=None,
        max_length=2000,
        description="Descripción detallada del producto",
        examples=["Laptop con procesador Intel i9, 32GB RAM, RTX 4090"],
    )

    price: Decimal = Field(
        ...,
        # gt =  greater than (mayor que). El precio debe ser mayor que 0
        # Un precio de 0 o negativo no tiene sentido en un e-commerce.
        gt= 0,
        description="Precio del producto. Máximo 2 decimales.",
        examples=["999.99"],
    )

    stock: int =  Field(
        default=0,
        # ge =  greater than or equal (mayor o igual que).
        # El stock puede ser 0 (agotado) pero nunca negativo.
        ge=0, 
        description="Unidades disponibles en inventario",
        examples=[50],
    )

    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Categoría del producto",
        examples=["Electronicos"],
    )

    # ================================================
    # VALIDADORES PERSONALIZADOS
    # ================================================
    # Los validadores son funciones que corren automáticamente
    # cuando Pydantic procesa ese campo. Si el validador lanza
    # un ValueError, Pydantic lo convierte en un error 422.

    # Le dice Pydantic que esta funcion valida el campo name
    @field_validator("name")
    # Los validadores reciben la clase(cls) en lugar de self porque el modelo
    #aún no esta creador
    @classmethod
    # Recibe el value que llego y lo devuelve un str ya validado o transformador
    def name_must_not_be_blank(cls, value: str) -> str:
        """
        Verifica que el nombre no sea solo espacios en blanco.
        Sin esto, alguien podría mandar name="  " y pasaría
        la validación min_length=1 porque tiene 3 caracteres.
        También limpiamos los espacios extra al inicio y final.
        """
        
        # stripped elimina los espacios con .strip() solo los de inicio o final
        stripped = value.strip()
        # detecta si el string queda vacio una ves aplicado el strip
        if not stripped:
            raise ValueError(
                "El nombre no puede ser solo espacios en blanco"
            )
        # Nos devuelve el valor ya transformado sin espacios
        return stripped

    @field_validator("category")
    @classmethod
    def category_to_lowercase(cls, value: Optional[str]) -> Optional[str]:
        """
        Normaliza las categorías a minúsculas.
        así 'Electronics', 'ELECTRONICS' y 'electronics' son
        la misma categoría. Sin esto, tendrías duplicados en la DB.
        """
        if value:
            return value.strip().lower()
        return value

    @field_validator("price")
    @classmethod
    def price_max_two_decimals(cls, value: Decimal) -> Decimal:
        """
        Verifica que el precio no tenga más de 2 decimales.
        as_tuple().exponent devuelve el número de decimales como
        negativo. Ejemplo:
            Decimal('999.99').as_tuple().exponent -> -2 (ok)
            Decimal('999.999').as_tuple().exponent -> -3 (rechazar)
        """
        if value.as_tuple().exponent < -2:
            raise ValueError(
                "El precio no puede tener más de 2 decimales"
            )
        return value

# ===============================
# SCHEMA DE CREACIÓN
# ===============================
class ProductCreate(ProductBase):
    """
    Schema para crear un producto.
    Se usa en: POST /api/v1/products

    Hereda todos los campos y validades de ProductBase.
    No agrega nada nuevo porque al crear un producto el cliente
    solo manda los datos del producto. El servidor genera
    automáticamente: id, is_active, created_at, update_at.

    Tener una clase separa (aunque esté vacía) es buena práctica
    porque si en el futuro necesitas agregar un campo solo para
    creación (como una contraseña) ya tienes el lugar correcto
    donde agregarlo sin tocar los otros schemas.
    """
    pass

# ======================================
# SCHEMA DE ACTUALIZACIÓN 
# ======================================
class ProductUpdate(BaseModel):
    """
    Schema para actualizar un producto.
    Se usa en: PUT /api/v1/products/{id}

    IMPORTANTE: hereda de BaseModel directamente, NO de ProductBase.
    ¿Por qué? Porque en ProductBase todos los campos obligatorios
    usan ... (son requeridos) pero al actualizar, el cliente solo
    manda los campos que quiere cambiar. No tiene sentido obligarlo a
    mandar el precio si solo quiere cambiar el nombre.

    Por eso aquí TODOS los campos son Optional con default=None.
    Esto se llama "partial update" o actualización parcial.
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Nuevo nombre del producto",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Nueva descripción del producto",
    )

    price: Optional[Decimal] = Field(
        default=None,
        gt=0,
        description="Nuevo precio del producto",
    )

    stock: Optional[int] = Field(
        default=None,
        ge=0,
        description="Nueva categoría del producto",
    )

    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Nueva categoría del producto",
    )

    is_active: Optional[bool]= Field(
        default=None,
        description="Estado activo/inactivo del producto",
    )

    @field_validator("name")
    @classmethod
    def name_muest_not_be_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("El nombre no puede ser solo espacios en blanco")
            return stripped
        return value
    

    @field_validator("category")
    @classmethod
    def category_to_lowercase(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            return value.strip().lower()
        return value
    
    @field_validator("price")
    @classmethod
    def price_max_two_decimals(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is not None:
            if value.as_tuple().exponent < -2:
                raise ValueError(
                    "El precio no puede tener más de 2 decimales"
                )
        return value
    
# ==================================
# SCHEMA DE RESPUESTA (un solo producto)
# ==================================
class ProductResponse(ProductBase):
    """
    Schema para las respuestas de la API.
    Se usa en todos los endpoints que devuelven un producto.

    Agrega los campos que genera el servidor:
    id, is_active, created_at, updated_at.

    El cliente los recibe en la respuesta pero nunca los manda al 
    crear o actualizar.
    """

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at:  datetime

    # model_config le dice a Pydantic Cómo comportarse.
    #
    # from_attributes=True es crítico. Sin esto, Pydantic solo
    # puede convertir diccionarios a schemas. Pero SQLALchemy
    # devuelve objetos Python. Así cuando FastAPI recibe un 
    # objeto Product de SQLALchemy y quiere convertirlo a
    # ProductResponse, funciona automáticamente.
    model_config = {"from_attributes": True}

# ==================================
# SCHEMA DE RESPUESTA (lista paginada)
# ==================================
class ProductListResponse(BaseModel):
    """
    Schema para devolver una lista de productos con metadatos
    de paginación.

    Siempre es mejor práctica devolver metadatos junto con las listas.
    Si devuelves solo el array, el cliente no sabe cuántos productos
    hay en total ni cuántas páginas existen. Tendría que hacer otra
    petición para saberlo.

    Con este schema, una respuesta se ve así:
    {
        "items": [...],
        "total": 150,
        "page": 1,
        "page_size": 20,
        "pages": 8,
    }
    """

    items: List[ProductResponse]
    total: int = Field(
        description="Total de productos en la base de datos"
    )
    page: int =  Field(
        description="Número de página actual"
    )
    page_size: int = Field(
        description="Cantidad de productos por página"
    )
    pages: int = Field(
        description="Total de páginas disponibles"
    )

    model_config = {"from_attributes": True}

# ==================================
# SCHEMA PARA VERIFICACIÓN DE STOCK
# ==================================
class StockCheckResponse(BaseModel):
    """
    Schema para la respuesta del endpoint de verificación de stock.
    Este endpoint lo usará el Orders Service para preguntar si
    hay suficiente stock antes de crear una orden.
    """

    product_id: UUID
    product_name: str
    requested_quantity: int
    available_stock: int
    is_available: bool = Field(
        description="True si hay suficiente stock para la cantidad solicitada"
    )

    model_config = {"from_attributes":True}
