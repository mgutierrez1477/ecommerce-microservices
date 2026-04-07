"""
routers/products.py
-------------------
Define los endpoints HTTP del Catalog

cadda función maneja un tipo específico de petición HTTP.
El router no tiene lógica de negocio ni habla con la DB directamente
Solo recibe peticiones, llama a crud.py , y devuelve respuestas.

Endpoints que exponemos:
    GET         /api/v1/products/               -> Listar productos
    GET         /api/v1/products/{product_id}   -> obtener uno
    POST        /api/v1/products/               -> crear producto
    PUT         /api/v1/products/{product_id}   -> actualizar producto
    DELETE      /api/v1/products/{product_id}   -> desactivar producto
    GET         /api/v1/products/{product_id}   -> verificar stock

"""

import math
from uuid import UUID 
from typing import Optional 


from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    StockCheckResponse,
)

import app.crud as crud


# ========================================
# CREAR EL ROUTER
# ========================================
# APIRouter agrupa endpoints relacionados bajo un mismo prefijo.
#
# prefix="/products" significa que todos los endpoints definidos
# aquí serán accesibles en /products/....
# Cuando registremos este router en main.py con el prefijo /api/v1,
# la ruta completa será /api/v1/products/...
#
# tags=["products"] agrupa estos endpoints en la documentación
# automáticamente de /docs. Todos aparecerán bajo la sección "products".

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

# =========================================
# GET /products/ - Listar productos
# =========================================
@router.get(
    "/",
    # response_model les dice a FastAPI qué schema usar para
    # serializar la respuesta. FastAPI toma el objeto que retornas
    # y lo convierte automáticamnete al formato de ProductListResponse
    # si el objeto tiene campos extra que no están en el schema,
    # FastAPI los ignora. Si faltan campos obligatorios, lanza error.
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK,
    summary="Listar productos",
    description="Obtiene una lista paginada de productos activos con filtros opcionales.",
)

def list_products(
    # Query() define parámetros que vienen en la UTL después del ?
    # Ejemplo: GET /products/?page=2&page_size=10&category=electronics
    # 
    # ge=1 valida que page sea mayor o igual a 1.
    # FastAPI retorna 422 automáticamente si mandan page=0 0 page=1.

    page: int = Query(
        default=1,
        ge=1,
        description="Número de página"
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        # le=100 evita que alguien pida 10,000 productos en una sola
        # petición y sature el servidor
        le = 100,
        description="Cantidad de productos por página (máximo 100)",
    ),
    category: Optional[str] = Query(
        default=None,
        description="Filtrar por categoría",
    ),
    # Depends (get_db) es la dependency injection de FastAPI
    # FastAPI llama a get_db(), obtiene la sesión de DB, y la
    # pasa como argumento db a esta función,
    # Al terminar el endpoint, FastAPI cierra la sesión automáticamente.
    db: Session = Depends(get_db),
): 
    products, total = crud.get_products(
        db=db,
        page=page,
        page_size=page_size,
        category=category,
    )

    # math.ceil redondea hacia arriba.
    # Si hay 21 productos con page_size=20: ceil(21/20)= 2 páginas
    # Si hay 20 productos con page_size=20: ceil(20/20)= 1 página
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return ProductListResponse(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
        pages=total_pages,
    )

# ======================================
# GET /products/{products_id} - Obtener uno
# ======================================
@router.get(
    # {product_id} es un path parameter. FastAPI extrae el valor
    # del URL automáticamente.
    # Ejemplo: GET /products/767bdb6e-5480-4636-8afe-b5634d5f5648
    # FastAPI extrae "767bdb6e-..." y lo pasa como product_id
    "/{product_id}",
    response_model=ProductResponse,
    status_code= status.HTTP_200_OK,
    summary="Obtener un producto por ID",
)
def get_product(
    # Al declarar product_id como UUID, FastAPI valid automáticamente
    # que el valor del URL sea un UUID valido
    # Si alguien hace GET /products/abc123
    # retorna 422 antes de que llegue a esta función.
    product_id: UUID,
    db: Session = Depends(get_db),
):
    product = crud.get_product_by_id(db, product_id)

    # crud.get_product_by_id devuelve None si no existe.
    # El router decide qué respuesta HTTP dar en ese caso.
    # HTTPException le dice a FastAPI que retorne un error HTTP
    # con el código y mensaje que especifiques.
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con id '{product_id}' no encontrado",
        )
    return product

# ======================================
# POST /products/ - Crear producto
# ======================================
@router.post(
    "/",
    response_model=ProductResponse,
    # 201 Created es más correcto que 200 OK para creación.
    # Indica que se creó un nuevo recurso, no solo que la petición
    # fue exitosa.
    status_code=status.HTTP_201_CREATED,
    summary="Crear nuevo producto",
)
def create_product(
    # product_data viene del body JSON de la petición.
    # FastAPI lo lee, lo valida con ProductCreate (Pydantic),
    # y si pasa la validación lo pasa como argumento.
    # Si no pasa la vlidación, retorna 422 automáticamente
    # con un mensaje descriptivo de qué campo falló y por qué.
    product_data: ProductCreate,
    db: Session = Depends(get_db),
):
    product = crud.create_product(db, product_data)
    return product

# ==================================
# PUT /products/{product_id} - Actualizar
# ==================================
@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar producto",
    description="Actualiza solo los campos enviados.",
)
def update_product(
    product_id: UUID,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
):
    product =  crud.update_product(db, product_id, product_data)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con id '{product_id}' no encontrado"
        )
    
    return product

# ===================================
# DELETE /products/{product_id} - Desactivar
# ===================================
@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Desactivar producto",
    description="Realiza un soft delete: marca el producto como inactivo sin borrar",
)
def deactivate_product(
    product_id: UUID,
    db: Session = Depends(get_db),
):
    product = crud.deactivate_product(db, product_id)

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con id '{product_id}' no encontrado",
        )
    
    return product

# =====================================
# GET /products/{product_id}/stock - Verificar stock
# =====================================
@router.get(
    "/{product_id}/stock",
    response_model=StockCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Verificar disponibilidad de stock",
    description="Usado por el Ordes Service para verificar stock antes de crear una orden",
)
def check_stock(
    product_id: UUID,
    quantity: int = Query(
        ge=1,
        description="Cantidad de unidades a verificar",
    ),
    db: Session = Depends(get_db),
): 
    has_stock, product = crud.check_stock_availability(
        db, product_id, quantity
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con id '{product_id}' no encontrado o inactivo",
        )
    
    return StockCheckResponse(
        product_id=product_id,
        product_name=product.name,
        requested_quantity=quantity,
        available_stock=product.stock,
        is_available=has_stock,
    )

