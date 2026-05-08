"""
catalog_client.py
--------------------------------
Cliente HTTP para comunicarse con el Catalog Service.

¿Por qué un archivo separado para esto?
Separation of Concerns. La lógica de comunicación con otro
servicio no debe estar mezclada con lada lógica de negocio
de las órdenes. Si mañana cambia la URL o la autenticación
del Catalog Service, solo modificas este archivo.

¿Por qué httpx y no request?
httpx soporta tanto request síncronos como asíncronos.
En microservicios donde múltiples servicios se comunican,
la comunicación asíncrona permite manejar más peticiones
simultáneas sin bloquear el servidor.
"""

import os
from decimal import Decimal
import httpx
from uuid import UUID
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# URL base del Catalog Service.
# En local: http://localhost:8001
# En docker Compose: http://catalog-service:8001
# Se configura via variable de entorno para que funcione
# en todos los entornos sin cambiar el codigo
CATALOG_SERVICE_URL = os.getenv(
    "CATALOG_SERVICE_URL",
    "http://localhost:8001"
)

# Timeout en segundos para las peticiones al Catalog Service.
# Si el Catalog tarda más de 5 segundos en responder,
# cancelamos la petición y retornamos error.
# Sin timeout, una petición lenta podría bloquear tu servidor indefinidamente.
REQUEST_TIMEOUT = 5.0

def get_product_info(
    product_id: UUID,
    quantity: int,
) -> Tuple[bool, Optional[dict]]:
    """
    Consulta el Catalog Service para verificar si un producto
    existe, está activo, y tiene suficiente stock.

    Parámetros:
        product_id -> UUID del producto a verificar
        quantity   -> cantidad que se quiere comprar
    
    Retorna:
        Tupla (disponible, info_del_producto)
        - (True, dict)  -> producto disponible con su info
        - (False, None) -> producto no disponible o error

    El dict de info contiene:
        product_id, product_name, unit_price, available_stock, is_available

    ¿Por qué no lanzamos excepción si el servicio falla?
    Porque queremos manejar el error graciosamente. Si el Catalog
    está caido, el Orders Service debe responder con un error
    descriptivo al cliente, no crashear.
    """
    try:
        # httpx.get hace una petición HTTP GET síncrona.
        # la URL llama al endpoint de verificación de stock
        # que creamos en el Catalog Service.
        url = (
            f"{CATALOG_SERVICE_URL}/api/v1/products"
            f"/{product_id}/stock"
        )

        response = httpx.get(
            url,
            params={"quantity": quantity},
            timeout=REQUEST_TIMEOUT,
        )

        # 404 significa que el producto no existe o está inactivo
        if response.status_code == 404:
            return False, None
        
        # Cualquier otro error del servidor
        if response.status_code != 200:
            print(
                f" Catalog Service respondío {response.status_code}"
                f"para el producto {product_id}"
            )
            return False, None

        data = response.json()

        # is_available viene del endpoint /stock del Catalog
        # True si hay suficiente stock para la cantidad solicitada
        return data["is_available"], data
    
    except httpx.TimeoutException:
        print(
            f" Timeout consultando Catalog Service"
            f"para producto {product_id}"
        )
        return False, None
    
    except httpx.ConnectError:
        print(
            "No se puede conectar al Catalog Service."
            f"URL: {CATALOG_SERVICE_URL}"
        )
        return False, None
    
    except Exception as e:
        print(f"Error inesperado consultando Catalog Service: {e}")
        return False, None
    
def get_product_price(product_id: UUID) -> Optional[Decimal]:
    """
    Obtiene el precio actual de un producto del Catalog Service.
    Se usa para calcular el total de la orden.
    """
    try: 
        url = f"{CATALOG_SERVICE_URL}/api/v1/products/{product_id}"
        response = httpx.get(url, timeout=REQUEST_TIMEOUT)

        if response.status_code != 200:
            return None
        
        return Decimal(response.json().get("price"))
    
    except Exception:
        return None