"""
test/test_products.py
---------------------
Tests del Catalog Service

Cada función que empieza con 'test_' es un test que pytest
ejecuta automáticamente.

Convención de nombres:
    test_[accion]_[contexto]_[resultado_esperado]

Ejemplos:
    test_create_product_valid_data_returns_201
    test_get_product_nonexistent_returns_404
    test_create_product_negative_price_returns_422
"""

from decimal import Decimal


# =================================
# DATOS DE PRUEBA
# Definimos los datos de prueba una sola vez aquí arriba.
# Si necesitas cambiar algo, lo cambias en un solo lugar.

VALID_PRODUCT = {
    "name": "Laptop Gaming ASUS ROG",
    "description": "Intel i9, 32GB RAM, RTX 4090",
    "price": 32999.99,
    "stock": 5,
    "category": "electronics",
}

VALID_PRODUCT_2 = {
    "name": "Monitor LG 4K",
    "price": 8999.99,
    "stock": 10,
    "category": "electronics",
}

# =====================================
# TESTS - CREAR PRODUCTO (POST)
# =====================================

def test_create_product_valid_data_returns_201(client):
    """
    Happy path: crear un producto con datos válidos.
    Debe retornar 201 y el producto creado con su UUID.
    """
    response = client.post("api/v1/products/", json=VALID_PRODUCT)

    assert response.status_code == 201, "El producto no se creó correctamente"

    data = response.json()
    # Verificamos que el servidor generó los campos automáticos
    assert "id" in data
    assert data["name"] ==  VALID_PRODUCT["name"]
    assert float(data["price"]) == VALID_PRODUCT["price"]
    assert data["stock"] == VALID_PRODUCT["stock"]
    assert data["category"] == VALID_PRODUCT["category"]
    # El servidor siempre crea productos activos
    assert data["is_active"] == True
    # Los timestamps deben existir
    assert "created_at" in data
    assert "updated_at" in data

def test_create_product_category_gets_lowercased(client):
    """
    El validador debe convertir la categoría a minúsculas.
    "ELECTRONICS" debe guardarse como "electronics"
    """
    product = {**VALID_PRODUCT, "category": "ELECTRONICS"}
    response = client.post("/api/v1/products", json=product)

    assert response.status_code == 201
    assert response.json()["category"] == "electronics"

def test_create_product_without_optional_fields(client):
    """
    Crear un producto sin campos opcionales (description, category).
    Solo name, price y stock son suficientes.
    """
    product = {
        "name" : "Producto Básico",
        "price": 100.00,
        "stock": 1,
    }
    response = client.post("/api/v1/products/", json=product)

    assert response.status_code == 201
    data = response.json()
    assert data["description"] is None
    assert data["category"] is None

def test_create_product_negative_price_returns_422(client):
    """
    Error case: precio negativo debe rechazarse con 422.
    El validador gt=0 de Pydantid debe bloquearlo.
    """
    product = {**VALID_PRODUCT, "price": -100}
    response = client.post("/api/v1/products/", json=product)

    assert response.status_code == 422

def test_create_product_zero_price_returns_422(client):
    """
    Error case: precio cero no tiene sentido en e-commerce.
    El validador gt=0 (mayor QUE, no mayor o igual) debe rechazarlo.
    """

    product = {**VALID_PRODUCT, "price": 0}
    response = client.post("/api/v1/products/", json=product)

    assert response.status_code == 422

def test_create_product_negative_stock_returns_422(client):
    """
    Error case: stock negativo no tiene sentido físicamente.
    """

    product = {**VALID_PRODUCT, "stock": -1}
    response = client.post("/api/v1/products/", json=product)

    assert response.status_code == 422

def test_create_product_blank_name_returns_422(client):
    """
    Error case: nombre solo con espacios debe rechazarse.
    El field_validator name_must_not_be_blank debe bloquearlo.
    """
    product = {**VALID_PRODUCT, "name": "  "}
    response = client.post("/api/v1/products/", json=product)

    assert response.status_code == 422

def test_create_product_missing_name_returns_422(client):
    """
    Error case: name es obligatorio (...)
    Sin él Pydantic debe rechazar la petición.
    """
    product = {"price": 999.99, "stock": 5}
    response = client.post("/api/v1/products/", json=product)

    assert response.status_code == 422

def test_create_product_missing_price_returns_422(client):
    """
    Error case : price es obligatorio
    """
    product = {"name": "Laptop", "stock": 5}
    response = client.post("/api/v1/products/")

    assert response.status_code == 422

# =======================================
# TESTS - OBTENER PRODUCTO (GET uno)
# =======================================

def test_get_product_existing_return_200(client):
    """
    Happy path: obtener un producto que existe.
    Pirmero lo creamos, luego lo buscamos por su ID
    """
    # Arrange: crear el producto
    create_response = client.post("/api/v1/products/", json=VALID_PRODUCT)
    product_id = create_response.json()["id"]

    # Act: obtenerlo por ID
    response = client.get(f"/api/v1/products/{product_id}")

    # Assert: debe retornar 200 con los datos correctos
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == VALID_PRODUCT["name"]

def test_get_product_nonexistent_returns_404(client):
    """
    Error case: buscar un UUID que no existe debe retornar 404.
    """
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/products/{fake_id}")

    assert response.status_code == 404
    # Verificamos que el mensaje de error es descriptivo
    assert "no encontrado" in response.json()["detail"]

def test_get_product_invalid_uuid_returns_422(client):
    """
    Error case: si el ID no es un UUID válido, FastAPI debe
    rechazarlo con 422 antes de llegar a la DB.
    """
    response = client.get("/api/v1/products/esto-no-es-un-uuid")
    
    assert response.status_code == 422

# ======================================
# TESTS - LISTAR PRODUCTOS (GET lista)
# ======================================

def test_list_products_empty_db_returns_empty_list(client):
    """
    Con DB vacía debe retornar lista vacía con metadatos en cero.
    """
    response = client.get("/api/v1/products/")

    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["pages"] == 0

def test_list_products_returns_correct_total(client):
    """
    Happy path: crear varios productos y verificar el total.
    """
    client.post("/api/v1/products/", json=VALID_PRODUCT)
    client.post("/api/v1/products/", json=VALID_PRODUCT_2)

    response = client.get("/api/v1/products/")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

def test_list_products_filter_by_category(client):
    """
    El filtro por categoría debe devolver solo los productos
    de esa categoría.
    """
    # Creamos uno de electronics y otro de otra categoria
    client.post("/api/v1/products/", json=VALID_PRODUCT)
    client.post("/api/v1/products/", json={
        **VALID_PRODUCT_2, "category":"peripherals"
    })

    response = client.get("/api/v1/products/?category=electronics")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["category"] == "electronics"

def test_list_products_pagination(client):
    """
    Edge case: la paginación debe devolver solo los productos
    del rango correcto.
    """
    # Creamos 3 productos
    client.post("/api/v1/products/", json=VALID_PRODUCT)
    client.post("/api/v1/products/", json=VALID_PRODUCT_2)
    client.post("/api/v1/products/", json={
        **VALID_PRODUCT, "name": "Teclado Mecánico"
    })

    # Pedimos page_size=2, debemos recibir 2 productos
    response = client.get("/api/v1/products/?page=1&page_size=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["pages"] == 2

# =======================================
# TESTS - ACTUALIZAR PRODUCTO (PUT)
# =======================================

def test_update_product_valid_data_returns_200(client):
    """
    Happy path: actualizar campos de un producto existente.
    """
    create_response = client.post("/api/v1/products/" ,json=VALID_PRODUCT)
    product_id = create_response.json()["id"]
    
    update_data = {"name": "Laptop Actualizada", "price": 29999.99}
    response = client.put(
        f"/api/v1/products/{product_id}",
        json=update_data,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Laptop Actualizada"
    assert float(data["price"]) == 29999.99
    # Los campos no enviados deben mantenerse igual
    assert data["stock"] == VALID_PRODUCT["stock"]

def test_update_product_nonexistent_returns_404(client):
    """
    Error case: actualizar un producto que no existe.
    """
    fake_id ="00000000-0000-0000-0000-000000000000"
    response = client.put(
        f"/api/v1/products/{fake_id}",
        json={"name": "No importa"},
    )

    assert response.status_code == 404

# ========================================
# TEST - DESACTIVAR PRODUCTO (DELETE)
# ========================================

def test_deactivate_product_returns_200(client):
    """
    Happy path: desactivar un producto existente.
    Debe retornar el producto con is_activate=False.
    """
    create_response = client.post("/api/v1/products/", json=VALID_PRODUCT)
    product_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/products/{product_id}")

    assert response.status_code == 200
    assert response.json()["is_active"] == False

def test_deactivated_product_not_in_list(client):
    """
    Un producto desactivado no debe aparecer en el listado normal.
    Esto verifica que el soft delete funciona correctamente.
    """
    create_response = client.post("/api/v1/products/", json=VALID_PRODUCT)
    product_id = create_response.json()["id"]

    # Desactivamos el producto
    client.delete(f"/api/v1/products/{product_id}")

    # El listado no debe incluirlo
    response = client.get("/api/v1/products/")
    data = response.json()
    assert data["total"] == 0

def test_deactivate_nonexistent_product_returns_404(client):
    """
    Error case: desactivar un producto que no existe.
    """
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.delete(f"/api/v1/products/{fake_id}")

    assert response.status_code == 404

# ========================================
# TEST - HEALTH CHECK
# ========================================

def tests_health_check_returns_200(client):
    """
    El health check siempre debe responder 200.
    Es lo que verifica la nube para saber si el servicio está vivo.
    """
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "catalog-service"

