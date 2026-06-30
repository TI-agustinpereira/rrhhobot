import os
from openai import OpenAI
from dotenv import load_dotenv

from db.connection import get_connection

"""
retriever.py

Archivo encargado de realizar las consultas a la base de datos, tanto por similitud como por clausula especifica. Devuelve chunks recuperados para generar repsuesta.
"""

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
TOP_K_DEFAULT = 4 # devuelve los K mas cercanos para rearmar el contexto

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChunkRecuperado:
    def __init__(self, texto, metadata, similitud):
        self.texto = texto
        self.metadata = metadata
        self.similitud = similitud # cociente entre vector query y vector resultado

def embeber_query(query: str) -> list[float]:
    """Genera el embedding para la consulta del usuario. Lo hace con el mismo modelo que se procesaron los chunks para que la similitud tenga algun significado"""
    response = client.embeddings.create(
        input=[query],
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def buscar_similares(query: str, top_k: int = TOP_K_DEFAULT, filtro_documento: str = None) -> list[ChunkRecuperado]:
    """
    Funcion encargada de buscar chunks similares a la consulta del usuario

    Params:
- query: string con la consulta del usuario a la cual se le van a buscar chunks similares

    Returns:
- lista de objetos ChunkRecuperado con los chunks mas similares a la consulta, su metadata

    """
    
    embedding = embeber_query(query)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if filtro_documento:
                cur.execute(
                """
                SELECT texto, metadata, 1 - (embedding <=> %s::vector) AS similitud
                FROM documentos
                WHERE metadata->>'documento' = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
            (embedding, filtro_documento, embedding, top_k)
)
            else:
                cur.execute(
                    """
                    SELECT
                        texto,
                        metadata,
                        1 - (embedding <=> %s::vector) AS similitud
                    FROM documentos
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (embedding, embedding, top_k)
                )
            filas = cur.fetchall()
    finally:
        conn.close() 

    return [ChunkRecuperado(texto=fila[0], metadata=fila[1], similitud=float(fila[2])) for fila in filas]

def buscar_por_clausula(clausula_id: str, documento: str = None) -> list[ChunkRecuperado]:

    """
    Funcion encargada de buscar chunks de una clausula especifica identificada por su id

    Params:
- clausula_id: string con el id de la clausula a buscar

    Returns:
- lista de objetos ChunkRecuperado con los chunks que corresponden a la clausula buscada, su metadata y similitud 1.0
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if documento:
                cur.execute(
                    """
                    SELECT texto, metadata, 1.0 AS similitud
                    FROM documentos
                    WHERE metadata->>'clausula_id' LIKE %s
                        AND metadata->>'documento'   = %s
                    ORDER BY metadata->>'clausula_id'
                    """,
                    (f"{clausula_id}%", documento)
                )
            else:
                cur.execute(
                    """
                    SELECT texto, metadata, 1.0 AS similitud
                    FROM documentos
                    WHERE metadata->>'clausula_id' LIKE %s
                    ORDER BY metadata->>'clausula_id'
                    """,
                    (f"{clausula_id}%",)
                )

            filas = cur.fetchall()
    finally:
        conn.close() 

    return [ChunkRecuperado(texto=fila[0], metadata=fila[1], similitud=float(fila[2])) for fila in filas]

if __name__ == "__main__":
    import sys

    query = sys.argv[1]
    print(f"\nBuscando: '{query}'")
    print("─" * 60)

    resultados = buscar_similares(query)

    for i, r in enumerate(resultados, 1):
        print(f"\n[{i}] Cláusula {r.metadata.get('clausula_id')} "f"— {r.metadata.get('clausula_titulo')}")
        print(f"    Documento: {r.metadata.get('documento')} "f"| Página: {r.metadata.get('pagina')} "f"| Similitud: {r.similitud:.3f}")
        print(f"    {r.texto[:200]}...")