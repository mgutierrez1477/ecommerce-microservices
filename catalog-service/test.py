from app.database import engine, Base, SessionLocal
from app.models import Product
from app.schemas import ProductCreate
from app import crud
from decimal import Decimal

# Creamos las tablas si no existen
Base.metadata.create_all(bind=engine)

# Abrimos una sesion
db = SessionLocal()

try:
    # Prueba 1: crear un producto
    nuevo = crud.create_product(db, ProductCreate(
        name='Laptop Gaming',
        price=Decimal('999.99'),
        stock=10,
        category='electronics'
    ))
    print(f'Prueba 1 OK - Producto creado con id: {nuevo.id}')

    # Prueba 2: leerlo por id
    encontrado = crud.get_product_by_id(db, nuevo.id)
    print(f'Prueba 2 OK - Producto encontrado: {encontrado.name}')

    # Prueba 3: listar productos
    productos, total = crud.get_products(db)
    print(f'Prueba 3 OK - Total en DB: {total}')

    # Prueba 4: verificar stock
    hay_stock, producto = crud.check_stock_availability(db, nuevo.id, 5)
    print(f'Prueba 4 OK - Hay stock para 5 unidades: {hay_stock}')

    # Prueba 5: desactivar
    desactivado = crud.deactivate_product(db, nuevo.id)
    print(f'Prueba 5 OK - Producto activo: {desactivado.is_active}')

    print('Todas las pruebas de crud.py pasaron correctamente')

finally:
    db.close()