import os
from openai import OpenAI
from dotenv import load_dotenv
import re

from rag.retriever import buscar_similares, buscar_por_clausula, ChunkRecuperado

"""
generator.py

Archivo encargado de recibir las consultas del usuario, detectar si hacen referencia a una clausula especifica o si requieren busqueda semantica y generar la respuesta
"""

load_dotenv()

OPENAI_MODEL = "gpt-4o-mini"
SIMILITUD_MINIMA = 0.40   # chunks por debajo de este umbral se descartan
TOP_K = 4      # chunks a recuperar por defecto

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
Eres un asistente especializado en recursos humanos y contratos laborales.
Respondés preguntas sobre contratos y normativas basándote exclusivamente en el contexto provisto.

Reglas:
- Respondé siempre en español.
- Usá únicamente la información del contexto para responder. No inventes datos.
- Si la información no está en el contexto, decí explícitamente que no encontraste esa información en el documento.
- Cuando la respuesta proviene de una cláusula específica, mencioná el número y título de la cláusula.
- Sé conciso y directo. No repitas el contexto completo, sintetizá la respuesta.
""".strip()

def construir_contexto(chunks: list[ChunkRecuperado]) -> str:

    if not chunks:
        return "No se encontraron fragmentos relevantes en el documento."

    partes = []
    for chunk in chunks:
        clausula_id = chunk.metadata.get("clausula_id", "?")
        clausula_titulo = chunk.metadata.get("clausula_titulo", "Sin título")
        documento = chunk.metadata.get("documento", "?")

        partes.append(f"[Cláusula {clausula_id} — {clausula_titulo} | Documento: {documento}]\n" f"{chunk.texto}")

    return "\n\n---\n\n".join(partes)

def detectar_clausula_referencial(query: str) -> str | None:
    """
    Detecta si la consulta hace referencia a una clausula.
    if true, devuelve el numero de la cláusula. if false, devuelve None.
    """

    patron = r'cl[aá]usula[s]?\s+([\d]+(?:\.[\d]+)*)'
    match = re.search(patron, query.lower())
    if match:
        return match.group(1)
    
    return None

def responder(query: str, filtro_documento: str = None, top_k: int = TOP_K) -> dict:

    clausula_id = detectar_clausula_referencial(query)

    if clausula_id:
        chunks = buscar_por_clausula(clausula_id, filtro_documento)
        modo = "referencial"
    else:
        chunks = buscar_similares(query, top_k, filtro_documento)
        modo = "semantico"

    # filtrar chunks por similitud minima (solo aplica a busqueda semantica)
    if modo == "semantico":
        chunks_filtrados = [c for c in chunks if c.similitud >= SIMILITUD_MINIMA]
        if not chunks_filtrados:
            return {
                "respuesta": "No encontre información suficientemente relevante en los documentos para responder esa pregunta.",
                "chunks": [],
                "modo": modo,
            }
        chunks = chunks_filtrados

    # armar contexto y llamar al LLM
    contexto = construir_contexto(chunks)

    # print(f"  Generando respuesta con {len(chunks)} chunks de contexto...")

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Contexto:\n{contexto}\n\n"
                f"Pregunta: {query}"
            )},
        ],
        temperature=0.2,   # algo de flexibilidad para sintetizar, pero sin inventar
    )

    respuesta = response.choices[0].message.content

    return {"respuesta": respuesta, "chunks": chunks, "modo": modo,}


if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:])
    print(f"\nPregunta: '{query}'")

    resultado = responder(query)

    print(f"Chunks usados: {len(resultado['chunks'])}")
    print(f"\nRespuesta:\n{resultado['respuesta']}")