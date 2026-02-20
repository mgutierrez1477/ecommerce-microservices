"""
database.py 
Configura la conexión a PostgreSQL usando SQLALchemy.
Todo el resto de la aplicación importa 'SessionLocal' y 'Base' desde aquí.
"""

from sqlalchemy import create_engine