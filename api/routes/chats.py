import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from rag.generator import responder

"""
chats.py

Router de FastAPI para el endpoint /chat.
Recibe la pregunta del usuario y devuelve la respuesta generada por el RAG.
"""

router = APIRouter(prefix="/chat", tags=["chat"])
MAX_QUERY_LEN = 1000
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    pregunta: str
    documento: str | None = None


class FuenteResponse(BaseModel):
    clausula_id: str
    clausula_titulo: str
    pagina: int
    similitud: float
    # documento no se expone — los nombres de archivos son confidenciales


class ChatResponse(BaseModel):
    respuesta: str
    fuentes: list[FuenteResponse]
    modo: str # "semantico" o "referencial"


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Endpoint principal del chatbot.
    Recibe una pregunta en lenguaje natural y devuelve la respuesta
    generada por el RAG junto con las fuentes utilizadas.
    """
    if len(request.pregunta) > MAX_QUERY_LEN:
        raise HTTPException(status_code=400, detail="La pregunta es demasiado larga")
    if not request.pregunta.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    try:
        resultado = responder(
            query=request.pregunta,
            filtro_documento=request.documento,
        )
    except Exception as e:
        logger.exception("Error procesando request")  # guarda el stack trace completo
        raise HTTPException(status_code=500, detail="Error interno del servidor.")

    fuentes = [
        FuenteResponse(
            clausula_id=     c.metadata.get("clausula_id", "?"),
            clausula_titulo= c.metadata.get("clausula_titulo", "?"),
            pagina=          c.metadata.get("pagina", 0),
            similitud=       round(c.similitud, 3),
        )
        for c in resultado["chunks"]
    ]

    return ChatResponse(
        respuesta=resultado["respuesta"],
        fuentes=fuentes,
        modo=resultado["modo"],
    )