import fitz          # para leer pdfs digitales
import pymupdf4llm   # para leer scans con ocr

from pathlib import Path
from dataclasses import dataclass

"""
pdf_ingestion.py

Archivo encargado de procesar los PDFs y devolver texto crudo legible para la LLM encargada de estructurarlo.
"""

MIN_CHARS_DIGITAL = 50 #umbral que uso para considerar si un pdf es digital o scan

#creo estructuras para no manejar diccionarios sueltos
@dataclass
class PageResult:
    page_number: int   # numero de pagina que empieza en 1
    tipo: str          # puede ser digital o escaneada
    texto: str         # el texto extraido



@dataclass
class DocumentResult:
    archivo: str
    paginas: list[PageResult]

    @property
    def texto_completo(self) -> str:
        return "\n\n".join(p.texto for p in self.paginas if p.texto.strip())

    @property
    def tiene_paginas_escaneadas(self) -> bool:
        return any(p.tipo == "escaneada" for p in self.paginas)

    @property
    def resumen(self) -> str:
        digitales = sum(1 for p in self.paginas if p.tipo == "digital")
        escaneadas = sum(1 for p in self.paginas if p.tipo == "escaneada")
        return (
            f"{self.archivo}: {len(self.paginas)} páginas | "
            f"{digitales} digitales, {escaneadas} escaneadas"
        )

def es_pagina_escaneada(pagina: fitz.Page) -> bool:
    """Determina si una pagina es un scan o un pdf digital basado en la cantidad de texto extraido."""

    texto = pagina.get_text().strip()
    return len(texto) < MIN_CHARS_DIGITAL

def extraer_pagina_digital(pagina: fitz.Page) -> str:
    """Extrae el texto de una pagina digital."""

    return pagina.get_text()

def extraer_pagina_scan(pdf_path: str, numero_pagina: int) -> str:
    """Extrae el texto de una pagina scan usando OCR."""

    texto_md = pymupdf4llm.to_markdown(pdf_path, pages=[numero_pagina])
    return texto_md

def procesar_pdf(pdf_path: str) -> DocumentResult:
    """
    Procesa un pdf y devuelve un DocumentResult con el texto de cada pagina y su tipo.
    
    Params:
- pdf_path: ruta al archivo PDF a procesar

    Returns:
- DocumentResult con el texto extraído de cada página y un resumen del documento

    Raises:
- FileNotFoundError si el archivo no existe
    """

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"El archivo no es un PDF: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    paginas = []
    for i, pagina in enumerate(doc):
        if es_pagina_escaneada(pagina):
            texto = extraer_pagina_scan(pdf_path, i)
            tipo = "escaneada"
        else:
            texto = extraer_pagina_digital(pagina)
            tipo = "digital"

        paginas.append(PageResult(page_number=i+1, tipo=tipo, texto=texto))

    doc.close()
    return DocumentResult(archivo=path.name, paginas=paginas)

def procesar_carpeta(carpeta: str) -> list[DocumentResult]:
    """
    Procesa todos los PDFs dentro de una carpeta
    
    Params:
- carpeta: ruta a la carpeta que contiene los archivos PDF a procesar

    Returns:
- lista de DocumentResult con el texto extraído de cada PDF y un resumen de cada uno

    Raises:
- FileNotFoundError si la carpeta no existe
    """

    carpeta_path = Path(carpeta)
    pdfs = sorted(carpeta_path.glob("*.pdf"))

    if not pdfs:
        print(f"No se encontraron PDFs en: {carpeta}")
        return []

    resultados = []
    for pdf in pdfs:
        print(f"\nProcesando: {pdf.name}")
        try:
            resultado = procesar_pdf(str(pdf))
            print(f"  ✓ {resultado.resumen}")
            resultados.append(resultado)
        except Exception as e:
            print(f"  ✗ Error procesando {pdf.name}: {e}")

    return resultados


# if __name__ == "__main__":
#     import sys

#     if len(sys.argv) < 2:
#         print("Uso: python pdf_ingestion.py <ruta_pdf_o_carpeta>")
#         sys.exit(1)

#     ruta = sys.argv[1]
#     path = Path(ruta)

#     if path.is_dir():
#         resultados = procesar_carpeta(ruta)
#         for r in resultados:
#             print(f"\n{'─'*60}")
#             print(r.resumen)
#             print(f"Primeros 300 caracteres:\n{r.texto_completo[:300]}")
#     elif path.is_file():
#         resultado = procesar_pdf(ruta)
#         print(f"\n{resultado.resumen}")
#         print(f"\nTexto completo extraído ({len(resultado.texto_completo)} caracteres):")
#         print(resultado.texto_completo[:500])
#     else:
#         print(f"Ruta no válida: {ruta}")
#         sys.exit(1)