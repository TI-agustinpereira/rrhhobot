import os
import json
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
from ingestion.chunker import Chunk
from db.connection import get_connection

"""
embedder.py

Archivo encargado de generar los embeddings de los chunks y cargarlos en la base de datos. Es el ultimo paso del pipeline de ingesta.
"""

EMBEDDING_MODEL     = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
BATCH_SIZE          = 20

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generar_embeddings(textos: list[str]) -> list[list[float]]:

    """Genera los embeddings para una lista de textos usando el modelo de OpenAI.
    
    Params:
- textos: lista de strings a los cuales generar embeddings

    Returns:
- lista de vectores (listas de floats) correspondientes a cada texto
"""

    response = client.embeddings.create(
        input=textos,
        model=EMBEDDING_MODEL
    )
    return [item.embedding for item in response.data]

def insertar_chunks(chunks, embeddings, conn):
    """Inserta los chunks con sus embeddings y metadata en la base de datos. Se asume que los chunks y embeddings están alineados por índice."""

    with conn.cursor() as cur:
        for chunk, embedding in zip(chunks, embeddings):
            cur.execute(
                "INSERT INTO documentos (texto, embedding, metadata) VALUES (%s, %s, %s)",
                (chunk.texto, embedding, json.dumps(chunk.metadata))
            )
    conn.commit()

def embeber_chunks(chunks: list[Chunk]) -> None:
    """
    Genera los embeddings para los chunks y los inserta en la base de datos. Maneja la inserción en batches para eficiencia.
    
    Params:
- chunks: lista de objetos Chunk a embeber e insertar en la base de datos

    Returns:
- None, pero inserta los chunks con sus embeddings y metadata en la base de datos

    Raises:
- RuntimeError si ocurre algún error durante la generación de embeddings o la inserción en la base de datos
    """

    conn = get_connection()
    try:
        insertados = 0 
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i: i + BATCH_SIZE]
            textos = [c.texto for c in batch]
            embeddings = generar_embeddings(textos)
            insertar_chunks(batch, embeddings, conn)
            insertados += len(batch)
            print(f"Insertados {insertados}/{len(chunks)} chunks...")
    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Error durante la carga: {e}")
    
    finally:
        print("Carga finalizada, cerrando conexión.")
        conn.close()

if __name__ == "__main__":
    import sys
    from ingestion.pdf_ingestion import procesar_pdf
    from ingestion.structurer import estructurar_documento
    from ingestion.chunker import generar_chunks

    if len(sys.argv) < 2:
        print("Uso: python embedder.py <ruta_pdf>")
        sys.exit(1)

    print(f"\nPaso 1 — Ingesta: {sys.argv[1]}")
    doc = procesar_pdf(sys.argv[1])
    print(f"Páginas procesadas: {len(doc.paginas)}")
    print(f"Texto extraído: {len(doc.texto_completo)} caracteres")

    print(f"\nPaso 2 — Estructuración...")
    clausulas = estructurar_documento(doc)

    print(f"\nPaso 3 — Chunking...")
    chunks = generar_chunks(clausulas)

    print(f"\nPaso 4 — Embedding y carga en Neon...")
    embeber_chunks(chunks)