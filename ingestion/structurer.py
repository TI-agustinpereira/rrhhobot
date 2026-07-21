import os
import re
import json
import unicodedata
import tiktoken
from openai import OpenAI
from dataclasses import dataclass
from dotenv import load_dotenv

from ingestion.pdf_ingestion import DocumentResult, PageResult

"""
structurer.py

Este archivo le da estructura a los resultados de ingesta de pdfs, pues las fuentes son diferentes entre pdfs
"""

load_dotenv()

SYSTEM_PROMPT = """
Eres un asistente especializado en análisis de contratos laborales y normativas de la empresa en cuanto a recursos humanos.
Tu principal labor es identificar las diferentes clausulas en el documento, etiquetandolas correctamente con el numero adjunto. En caso de no haber tal numero, segregalas en base al contexto.
Tu trabajo es rellenar los campos vacios de la siguiente plantilla JSON, insertando la cantidad de clausulas que identifiques en el documento.
Devuelve UNICAMENTE un JSON valido con la siguiente estructura, sin texto adicional, sin bloques de codigo markdown, sin explicaciones:
{
    "clausulas": [
    {
        "id": "",
        "titulo": "",
        "texto": "",
        "seccion": "",
        "pagina": 1
    },
    {
        "id": "",
        "titulo": "",
        "texto": "",
        "seccion": "",
        "pagina": 3
    }
    ]
}
El campo "texto" debe contener el cuerpo completo de la clausula sin modificaciones.
El campo "pagina" es donde comienza la clausula. Si no podés determinarlo, usá 0.
El campo "id" debe ser un identificador unico para cada clausula, preferentemente basado en el numero de clausula o seccion. Si no hay tal numero, inventalo de forma consistente (ej: clausula_1, clausula_2, etc).
El campo "titulo" debe ser el titulo de la clausula, si es que existe.
El campo "seccion" es opcional, pero si el documento tiene divisiones claras (ej: "Sección 1: Obligaciones del Empleado"), usalo para agrupar clausulas bajo esa sección.
""".strip()

OPENAI_MODEL = "gpt-4o-mini"
MAX_TOKENS_CLAUSULA = 500
ENCODING_NAME = "cl100k_base"

client  = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
encoder = tiktoken.get_encoding(ENCODING_NAME)

@dataclass
class Clausula:
    id: str
    titulo: str
    texto: str
    pagina: int
    documento: str

def contar_tokens(texto: str) -> int:
    """Convierte un string en tokens usando el mismo metodo que usa OpenAI internamente."""
    return len(encoder.encode(texto))

def subdividir_clausula(clausula: dict, documento: str) -> list[Clausula]:
    """
    En caso de que el documento supere el umbral de 500 tokens, se divide para mantener granularidad en la respuesta.
    
    Params:
- clausula: diccionario con los campos de la clausula a subdividir

    Returns:
- lista de clausulas resultantes de subdividir la clausula original, con ids modificados para mantener unicidad
    """

    texto = clausula["texto"]
    parrafos = [p.strip() for p in texto.split("\n\n") if p.strip()]
    fragmento_actual = ""
    sub_index = 1
    resultado = []

    for parrafo in parrafos:
        candidato = (fragmento_actual + "\n\n" + parrafo).strip()
        if contar_tokens(candidato) <= MAX_TOKENS_CLAUSULA:
            fragmento_actual = candidato
        else:
            if fragmento_actual:
                resultado.append(Clausula(
                    id=f"{clausula['id']}.{sub_index}",
                    titulo=clausula["titulo"],
                    texto=fragmento_actual,
                    pagina=clausula.get("pagina", 0),
                    documento=documento,
                ))
                sub_index += 1
            fragmento_actual = parrafo

    if fragmento_actual:
        resultado.append(Clausula(
            id=f"{clausula['id']}.{sub_index}",
            titulo=clausula["titulo"],
            texto=fragmento_actual,
            pagina=clausula.get("pagina", 0),
            documento=documento,
        ))

    return resultado

def llamar_llm(texto_documento: str) -> list[dict]:
    """Llama al modelo de OpenAI para extraer las clausulas del texto del documento."""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"Extraé las cláusulas...{texto_documento}"},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )
    contenido = response.choices[0].message.content
    print(f"  Respuesta raw del LLM: {contenido}")
    data = json.loads(contenido)
    return data.get("clausulas", [])

PREFIJO_MATCH = 40   # caracteres del inicio de la clausula usados para ubicar la pagina

def _normalizar(texto: str) -> str:
    """
    Normaliza texto para comparar el OCR de una pagina contra el texto que devolvio
    el LLM: saca acentos, pasa a minusculas, elimina puntuacion y colapsa espacios.
    Asi el match no falla por diferencias de tildes/espacios/mayusculas.
    """
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))  # saca acentos
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9 ]", " ", texto)   # saca puntuacion
    texto = re.sub(r"\s+", " ", texto).strip()  # colapsa espacios
    return texto

def calcular_pagina(texto_clausula: str, paginas: list[PageResult]) -> int:
    """
    Determina en que pagina empieza una clausula, buscando el prefijo de su texto
    (normalizado) dentro del texto de cada pagina.

    Params:
- texto_clausula: el cuerpo de la clausula devuelto por el LLM (sin overlap todavia)
- paginas: lista de PageResult del documento, en orden

    Returns:
- el page_number de la primera pagina que contiene el prefijo, o 0 si no se encuentra
    """
    prefijo = _normalizar(texto_clausula)[:PREFIJO_MATCH]
    if not prefijo:
        return 0

    for pagina in paginas:
        if prefijo in _normalizar(pagina.texto):
            return pagina.page_number

    return 0

def estructurar_documento(doc_result: DocumentResult) -> list[Clausula]:
    """
    Toma el resultado de la ingesta de un pdf y devuelve una lista de clausulas estructuradas.
    
    Params:
- doc_result: resultado de procesar un pdf, con el texto completo y metadata

    Returns:
- lista de clausulas estructuradas con id, titulo, texto, pagina y documento

    Raises:
- ValueError si el texto del documento está vacío o si ocurre algún error durante la llamada al LLM
    """

    texto = doc_result.texto_completo

    if not texto.strip():
        raise ValueError(f"El documento {doc_result.archivo} no tiene texto extraíble.")
    
    clausulas_raw = llamar_llm(texto)
    print(f"  LLM identificó {len(clausulas_raw)} cláusulas")

    # pisar la pagina que adivino el LLM con la pagina real (matching contra el OCR).
    # Se hace aca, sobre el texto limpio de la clausula, ANTES de que el chunker
    # le agregue el overlap de la clausula anterior (que arruinaria el match).
    for clausula_dict in clausulas_raw:
        clausula_dict["pagina"] = calcular_pagina(
            clausula_dict.get("texto", ""), doc_result.paginas
        )

    for c in clausulas_raw:
        print(f"  ID: {c.get('id')} | Pág: {c.get('pagina')} | Titulo: {c.get('titulo')} | Texto[:50]: {c.get('texto','')[:50]}")

    clausulas = []

    for clausula_dict in clausulas_raw:
        tokens = contar_tokens(clausula_dict.get("texto", ""))

        if tokens > MAX_TOKENS_CLAUSULA:
            sub_clausulas = subdividir_clausula(clausula_dict, doc_result.archivo)
            clausulas.extend(sub_clausulas)
        else:
            clausulas.append(Clausula(
                id=str(clausula_dict.get("id", "")),
                titulo=clausula_dict.get("titulo", "Sin título"),
                texto=clausula_dict.get("texto", ""),
                pagina=clausula_dict.get("pagina", 0),
                documento=doc_result.archivo,
            ))

    print(f"  Total chunks generados: {len(clausulas)}")
    return clausulas