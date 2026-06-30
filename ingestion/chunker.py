import tiktoken
from dataclasses import dataclass, field
from ingestion.structurer import Clausula

"""
chunker.py

Archivo encargado de tomar las clausulas estructuradas y generar los chunks que se van a embeber
"""

OVERLAP_TOKENS = 50
ENCODING_NAME  = "cl100k_base"

encoder = tiktoken.get_encoding(ENCODING_NAME)

@dataclass
class Chunk:
    texto: str
    metadata: dict = field(default_factory=dict)

def contar_tokens(texto: str) -> int:
    return len(encoder.encode(texto))

def obtener_ultimos_tokens(texto: str, n_tokens: int) -> str:
    """
    Obtiene los ultimos n_tokens tokens y los decodifica a texto
    
    Params:
- texto: el texto del cual obtener los tokens
- n_tokens: la cantidad de tokens a obtener desde el final del texto

    Returns:
- el texto correspondiente a los ultimos n_tokens tokens
    """
    tokens = encoder.encode(texto)
    if len(tokens) <= n_tokens:
        return texto
    else:
        return encoder.decode(tokens[-n_tokens:])
    
def generar_chunks(clausulas: list[Clausula]) -> list[Chunk]:
    """
    Funcion encargada de generar chunks a partir de clausulas estructuradas, agregando overlap para manejar contexto. Principal funcion del archivo

    Params:
- clausulas: lista de clausulas estructuradas a partir de las cuales generar los chunks

    Returns:
- lista de chunks generados a partir de las clausulas, con metadata relevante para luego identificar
    """
    chunks: list[Chunk] = []

    for i, clausula in enumerate(clausulas):
        tiene_overlap = False
        texto_chunk = clausula.texto
        if i > 0:
            texto_anterior = clausulas[i-1].texto
            overlap = obtener_ultimos_tokens(texto_anterior, OVERLAP_TOKENS)

            if overlap.strip():
                texto_chunk = overlap + "\n\n" + texto_chunk
                tiene_overlap = True
        chunks.append(Chunk(
            texto=texto_chunk,
            metadata={
    "clausula_id":     clausula.id,
    "clausula_titulo": clausula.titulo,
    "pagina":          clausula.pagina,
    "documento":       clausula.documento,
    "tiene_overlap":   tiene_overlap,
}
        ))
    print("chunks generados:", len(chunks))
    return chunks

# if __name__ == "__main__":
#     import sys
#     from ingestion.pdf_ingestion import procesar_pdf
#     from ingestion.structurer import estructurar_documento

#     if len(sys.argv) < 2:
#         print("Uso: python chunker.py <ruta_pdf>")
#         sys.exit(1)

#     print(f"\nPaso 1 — Ingesta: {sys.argv[1]}")
#     doc = procesar_pdf(sys.argv[1])

#     print(f"\nPaso 2 — Estructuración...")
#     clausulas = estructurar_documento(doc)

#     print(f"\nPaso 3 — Chunking...")
#     chunks = generar_chunks(clausulas)

#     print(f"\nResultado: {len(chunks)} chunks generados\n")
#     for c in chunks:
#         tokens = contar_tokens(c.texto)
#         overlap_str = "con overlap" if c.metadata["tiene_overlap"] else "sin overlap"
#         print(f"  [{c.metadata['clausula_id']}] {c.metadata['clausula_titulo']} "f"— {tokens} tokens — {overlap_str}")