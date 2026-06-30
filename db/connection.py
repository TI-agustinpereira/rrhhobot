import os
import psycopg2
from dotenv import load_dotenv

"""
connection.py

Archivo que establece la conexion a la base de datos neon y verifica la extension vectorial exista.
"""

load_dotenv()

def get_connection():

    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL no esta configurada en las variables de entorno")
    
    return psycopg2.connect(url)

def verificar_conexion():

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            
    except Exception as e:
        raise RuntimeError(f"Error al verificar la conexion: {e}")

    finally:
        conn.close()